import time
import os
import sys
import json
import glob
import codecs
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

# Force UTF-8 encoding for stdin/stdout/stderr
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
if sys.stdin.encoding != 'utf-8':
    sys.stdin = codecs.getreader('utf-8')(sys.stdin.buffer, 'strict')

# Set default encoding to UTF-8
import locale
locale.getpreferredencoding = lambda: 'UTF-8'

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
    print(f"Getting telegram app for sender: {sender_id}")
    if sender_id not in telegram_apps:
        token = os.getenv(f'{sender_id.upper()}_TELEGRAM_BOT_TOKEN')
        print(f"Looking for token: {sender_id.upper()}_TELEGRAM_BOT_TOKEN")
        print(f"Token found: {bool(token)}")
        
        # Only default to KINOS if sender's token not found
        if not token:
            token = os.getenv('KINOS_TELEGRAM_BOT_TOKEN')
            print(f"No bot token found for {sender_id}, defaulting to KINOS bot")
            
        if token:
            try:
                # Import inside function to ensure clean initialization
                from telegram.ext import Application
                
                # Create application with minimal configuration
                telegram_apps[sender_id] = (
                    Application.builder()
                    .token(token)
                    .http_version("1.1")  # Use HTTP 1.1 instead of default HTTP/2
                    .get_updates_http_version("1.1")
                    .build()
                )
                
            except Exception as e:
                print(f"Error creating Telegram app for {sender_id}: {str(e)}")
                return None
                
    return telegram_apps.get(sender_id)

class RepositoryChangeHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.processed_messages = set()  # Track processed messages

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

        # Check if this is a message file we've already processed
        if 'data/messages' in file_path and file_path in self.processed_messages:
            logging.info(f"Skipping already processed message: {file_path}")
            return
            
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
                        # Add file to processed set
                        self.processed_messages.add(file_path)
                        # Check if we've sent a message recently
                        current_time = time.time()
                        if hasattr(self, 'last_message_time'):
                            time_since_last = current_time - self.last_message_time
                            if time_since_last < 2:
                                await asyncio.sleep(2 - time_since_last)
                        
                        message = f"{data['content']}"
                        await self._send_telegram_message(message, data['senderId'])
                        self.last_message_time = time.time()
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
                
        # Handle specification files
        elif 'data/specifications' in file_path and event_type in ['created', 'modified'] and file_path.endswith('.json'):
            try:
                # Wait a brief moment to ensure file is fully written
                await asyncio.sleep(0.1)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.loads(f.read())
                    if 'specificationId' in data and 'collaborationId' in data:
                        # Load collaboration to get client swarm
                        collab_files = glob.glob('data/collaborations/*.json')
                        client_swarm_id = None
                        for collab_file in collab_files:
                            with open(collab_file, 'r', encoding='utf-8') as cf:
                                collab_data = json.load(cf)
                                if collab_data.get('collaborationId') == data['collaborationId']:
                                    client_swarm_id = collab_data.get('clientSwarmId')
                                    break
                        
                        if client_swarm_id:
                            # Create a more detailed message including content preview
                            content_preview = data.get('content', '')[:200] + '...' if len(data.get('content', '')) > 200 else data.get('content', '')
                            message = (f"📋 New Specification\n\n"
                                     f"Title: {data.get('title')}\n"
                                     f"Created: {data.get('createdAt')}\n\n"
                                     f"Preview:\n{content_preview}\n\n"
                                     f"View full specification at:\n"
                                     f"https://swarms.universalbasiccompute.ai/specifications/{data['specificationId']}")
                            await self._send_telegram_message(message, client_swarm_id)
                            print(f"Sent specification notification to {client_swarm_id}")
                            
            except Exception as e:
                print(f"Error processing specification file {file_path}: {e}")
                
        # Handle deliverable files
        elif 'data/deliverables' in file_path and event_type in ['created', 'modified'] and file_path.endswith('.json'):
            try:
                # Wait a brief moment to ensure file is fully written
                await asyncio.sleep(0.1)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.loads(f.read())
                    if 'deliverableId' in data and 'collaborationId' in data:
                        # Load collaboration to get client swarm
                        collab_files = glob.glob('data/collaborations/*.json')
                        client_swarm_id = None
                        for collab_file in collab_files:
                            with open(collab_file, 'r', encoding='utf-8') as cf:
                                collab_data = json.load(cf)
                                if collab_data.get('collaborationId') == data['collaborationId']:
                                    client_swarm_id = collab_data.get('clientSwarmId')
                                    break
                        
                        if client_swarm_id:
                            # Create a message with content preview
                            content_preview = data.get('content', '')[:200] + '...' if len(data.get('content', '')) > 200 else data.get('content', '')
                            message = (f"📦 New Deliverable\n\n"
                                     f"Title: {data.get('title')}\n"
                                     f"Created: {data.get('createdAt')}\n\n"
                                     f"Preview:\n{content_preview}\n\n"
                                     f"View full deliverable at:\n"
                                     f"https://swarms.universalbasiccompute.ai/deliverables/{data['deliverableId']}")
                            await self._send_telegram_message(message, client_swarm_id)
                            print(f"Sent deliverable notification to {client_swarm_id}")
                            
            except Exception as e:
                print(f"Error processing deliverable file {file_path}: {e}")

    async def _send_telegram_message(self, message, sender_id):
        try:
            # Rate limiting
            current_time = time.time()
            if hasattr(self, '_last_message_time'):
                time_since_last = current_time - self._last_message_time
                if time_since_last < 3:
                    await asyncio.sleep(3 - time_since_last)
            self._last_message_time = current_time

            logging.info(f"Sending message from {sender_id}")
            
            # Get message data to find collaboration
            message_files = glob.glob('data/messages/*.json')
            collab_id = None
            for msg_file in message_files:
                with open(msg_file, 'r', encoding='utf-8') as f:
                    msg_data = json.load(f)
                    if msg_data.get('senderId') == sender_id and msg_data.get('content') == message:
                        collab_id = msg_data.get('collaborationId')
                        break

            # Get client from collaboration if it exists
            client_swarm_id = None
            if collab_id:
                collab_file = f'data/collaborations/{collab_id}.json'
                if os.path.exists(collab_file):
                    with open(collab_file, 'r', encoding='utf-8') as f:
                        collab_data = json.load(f)
                        client_swarm_id = collab_data.get('clientSwarmId')
            
            # If no collaboration found, fall back to receiverId
            if not client_swarm_id:
                for msg_file in message_files:
                    with open(msg_file, 'r', encoding='utf-8') as f:
                        msg_data = json.load(f)
                        if msg_data.get('senderId') == sender_id and msg_data.get('content') == message:
                            client_swarm_id = msg_data.get('receiverId')
                            break
            
            # Get chat ID from client's swarm data
            chat_id = None
            if client_swarm_id:
                # First try to get from swarm file
                swarm_file = f'data/swarms/{client_swarm_id}.json'
                if os.path.exists(swarm_file):
                    with open(swarm_file, 'r', encoding='utf-8') as f:
                        swarm_data = json.load(f)
                        chat_id = swarm_data.get('telegramChatId')
            
                # If not found in swarm file, try environment variable
                if not chat_id:
                    chat_id_key = f"{client_swarm_id.upper()}_TELEGRAM_CHAT_ID"
                    chat_id = os.getenv(chat_id_key)
                    if chat_id:
                        chat_id = int(chat_id)  # Convert string to integer for Telegram

            # If still no chat_id, fall back to KINOS chat
            if not chat_id:
                chat_id = int(os.getenv('KINOS_TELEGRAM_CHAT_ID'))
                logging.info(f"Falling back to KINOS chat ID for message from {sender_id}")
            
            # Get appropriate bot token and app
            app = get_telegram_app(sender_id)
                    
            if app and chat_id:
                print(f"Sending message as {sender_id} to client {client_swarm_id} (chat {chat_id})")
                await app.bot.send_message(chat_id=chat_id, text=message)
            else:
                print(f"Could not send message - Missing {'app' if not app else 'chat_id'}")
                print(f"Sender: {sender_id}")
                print(f"Client: {client_swarm_id}")
                print(f"Chat ID: {chat_id}")
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            print(f"Sender: {sender_id}")
            print(f"Client: {client_swarm_id if 'client_swarm_id' in locals() else 'Not found'}")
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
