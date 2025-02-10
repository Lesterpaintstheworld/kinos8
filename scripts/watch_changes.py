import time
import os
import json
import glob
import subprocess
import logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio
from telegram.ext import ApplicationBuilder
from dotenv import load_dotenv
from pyairtable import Api
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(
    filename='watch_changes.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

# Get API keys from environment variables
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
if not AIRTABLE_API_KEY:
    raise ValueError("AIRTABLE_API_KEY environment variable is required")

BASE_ID = os.getenv('AIRTABLE_BASE_ID')
if not BASE_ID:
    raise ValueError("AIRTABLE_BASE_ID environment variable is required")

# Initialize Airtable API
api = Api(AIRTABLE_API_KEY)

# Cache for Telegram applications and event loops
telegram_apps = {}
loop = None

def get_telegram_app(sender_id):
    """Get or create Telegram application for a sender"""
    if sender_id not in telegram_apps:
        # Use specific token for kinos or xforge
        if sender_id in ['kinos', 'xforge']:
            token = os.getenv(f'{sender_id.upper()}_TELEGRAM_BOT_TOKEN')
            if token:
                telegram_apps[sender_id] = ApplicationBuilder().token(token).build()
                return telegram_apps[sender_id]
        else:
            token_key = f"{sender_id.upper()}_TELEGRAM_BOT_TOKEN"
            token = os.getenv(token_key)
            if token:
                telegram_apps[sender_id] = ApplicationBuilder().token(token).build()
    return telegram_apps.get(sender_id)

class RepositoryChangeHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.processed_messages = set()  # Add set to track processed messages

    def on_created(self, event):
        if event.is_directory:
            return
        self.loop.run_until_complete(self._handle_file_event("created", event.src_path))

    def on_modified(self, event):
        if event.is_directory:
            return
        self.loop.run_until_complete(self._handle_file_event("modified", event.src_path))

    def on_deleted(self, event):
        if event.is_directory:
            return
        self.loop.run_until_complete(self._handle_file_event("deleted", event.src_path))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def push_to_airtable(self, file_path):
        """Push changes to Airtable based on file type with retry logic"""
        try:
            # Convert path to use forward slashes for consistency
            file_path = file_path.replace('\\', '/')
            
            # Determine file type and table
            if 'data/messages' in file_path:
                table = api.table(BASE_ID, 'Messages')
                id_field = 'messageId'
            elif 'data/news' in file_path:
                table = api.table(BASE_ID, 'News')
                id_field = 'newsId'
            elif 'data/swarms' in file_path:
                table = api.table(BASE_ID, 'Swarms')
                id_field = 'swarmId'
            elif 'data/collaborations' in file_path:
                table = api.table(BASE_ID, 'Collaborations')
                id_field = 'collaborationId'
            elif 'data/services' in file_path:
                table = api.table(BASE_ID, 'Services')
                id_field = 'serviceId'
            elif 'data/specifications' in file_path:
                table = api.table(BASE_ID, 'Specifications')
                id_field = 'specificationId'
            elif 'data/deliverables' in file_path:
                table = api.table(BASE_ID, 'Deliverables')
                id_field = 'deliverableId'
            elif 'data/validations' in file_path:
                table = api.table(BASE_ID, 'Validations')
                id_field = 'validationId'
            else:
                return
            
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get existing records
            existing_records = table.all()
            existing_ids = {record['fields'].get(id_field): record['id'] 
                          for record in existing_records 
                          if id_field in record['fields']}
            
            # Get record ID from data
            record_id = data.get(id_field)
            if not record_id:
                print(f"Warning: Missing {id_field} in {file_path}")
                return
                
            # Update or create record
            if record_id in existing_ids:
                table.update(existing_ids[record_id], data)
                print(f"Updated {id_field}: {record_id} in Airtable")
            else:
                table.create(data)
                print(f"Created new {id_field}: {record_id} in Airtable")
                
        except Exception as e:
            print(f"Error pushing to Airtable: {e}")

    async def _handle_file_event(self, event_type, file_path):
        # Convert path to use forward slashes for consistency
        file_path = file_path.replace('\\', '/')
        
        # Skip git and temporary files
        if '.git' in file_path or file_path.endswith('.tmp'):
            return
            
        # Add delay to ensure file writes are complete
        await asyncio.sleep(0.5)
        
        logging.info(f"Processing {event_type} event for file: {file_path}")
            
        try:
            # Git push after any file change
            print("Pushing changes to git...")
            subprocess.run(["git", "push"], check=True)
            
            # Push to Airtable if file is created or modified
            if event_type in ['created', 'modified'] and file_path.endswith('.json'):
                await self.push_to_airtable(file_path)
        except subprocess.CalledProcessError as e:
            print(f"Error pushing to git: {e}")
            
        # Only process created/modified JSON files in data/messages
        if 'data/messages' in file_path and event_type in ['created', 'modified'] and file_path.endswith('.json'):
            try:
                # Wait a brief moment to ensure file is fully written
                await asyncio.sleep(0.1)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.loads(f.read())
                    if 'content' in data and 'senderId' in data and 'messageId' in data:
                        # Check if we've already processed this message
                        if data['messageId'] in self.processed_messages:
                            print(f"Skipping duplicate message {data['messageId']}")
                            return
                            
                        # Check if we've sent a message recently
                        current_time = time.time()
                        if hasattr(self, 'last_message_time'):
                            time_since_last = current_time - self.last_message_time
                            if time_since_last < 2:
                                await asyncio.sleep(2 - time_since_last)
                        
                        message = f"{data['content']}"
                        await self._send_telegram_message(message, data['senderId'])
                        self.last_message_time = time.time()
                        
                        # Mark message as processed
                        self.processed_messages.add(data['messageId'])
                        print(f"Processed message {data['messageId']}")
            except Exception as e:
                print(f"Error processing message file {file_path}: {e}")
                
        # Handle news files
        elif 'data/news' in file_path and event_type in ['created', 'modified'] and file_path.endswith('.json'):
            try:
                # Wait a brief moment to ensure file is fully written
                await asyncio.sleep(0.1)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.loads(f.read())
                    if 'content' in data and 'swarmId' in data:
                        message = f"News: {data['content']}"
                        await self._send_telegram_message(message, data['swarmId'])
                        self.last_message_time = time.time()
                        print(f"Processed news from {data['swarmId']}")
            except Exception as e:
                print(f"Error processing news file {file_path}: {e}")

    async def _send_telegram_message(self, message, sender_id):
        try:
            # Rate limiting
            current_time = time.time()
            if hasattr(self, '_last_message_time'):
                time_since_last = current_time - self._last_message_time
                if time_since_last < 3:  # Minimum 3 seconds between messages
                    await asyncio.sleep(3 - time_since_last)
            self._last_message_time = current_time

            logging.info(f"Sending message from {sender_id}")
            
            # Use KinOS or XForge token based on sender
            if sender_id in ['kinos', 'xforge']:
                # Get bot token based on sender
                token_key = f"{sender_id.upper()}_TELEGRAM_BOT_TOKEN"
                app = get_telegram_app(sender_id)
                
                # Get most recent message file for receiver ID
                message_files = glob.glob('data/messages/*.json')
                latest_file = max(message_files, key=os.path.getctime)
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    receiver_id = data.get('receiverId')
                    if receiver_id:
                        chat_id_key = f"{receiver_id.upper()}_TELEGRAM_CHAT_ID"
                        chat_id = os.getenv(chat_id_key)
            else:
                # For other senders, use their own chat ID
                chat_id_key = f"{sender_id.upper()}_TELEGRAM_CHAT_ID"
                chat_id = os.getenv(chat_id_key)
                app = get_telegram_app(sender_id)
                
            if app and chat_id:
                print(f"Sending message as {sender_id} to chat {chat_id}")
                await app.bot.send_message(chat_id=chat_id, text=message)
            else:
                print(f"Telegram credentials not configured for {'receiver' if sender_id in ['kinos', 'xforge'] else 'sender'} {sender_id}")
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            print(f"Sender: {sender_id}")
            print(f"Chat ID: {chat_id if 'chat_id' in locals() else 'Not found'}")

def main():
    # Path to watch (current directory)
    path = "."
    
    # Create event handler and observer
    event_handler = RepositoryChangeHandler()
    observer = Observer()
    
    # Schedule the observer
    observer.schedule(event_handler, path, recursive=True)
    
    # Start the observer
    observer.start()
    print(f"Watching repository for changes...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped watching repository")
        
    observer.join()

if __name__ == "__main__":
    main()
