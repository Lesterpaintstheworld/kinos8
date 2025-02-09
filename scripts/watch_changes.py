import time
import os
import json
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio
from telegram.ext import ApplicationBuilder
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Cache for Telegram applications and event loops
telegram_apps = {}
loop = None

def get_telegram_app(sender_id):
    """Get or create Telegram application for a sender"""
    if sender_id not in telegram_apps:
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

    async def _handle_file_event(self, event_type, file_path):
        # Convert path to use forward slashes for consistency
        file_path = file_path.replace('\\', '/')
        
        # Skip git and temporary files
        if '.git' in file_path or file_path.endswith('.tmp'):
            return
            
        try:
            # Git push after any file change
            print("Pushing changes to git...")
            subprocess.run(["git", "push"], check=True)
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
            # If sender is kinos, use the receiver's chat ID and token
            if sender_id == 'kinos':
                # Get message data to find receiver
                file_path = None
                for root, dirs, files in os.walk('data/messages'):
                    for file in files:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            data = json.loads(f.read())
                            if data.get('content') == message:
                                receiver_id = data.get('receiverId')
                                if receiver_id:
                                    chat_id_key = f"{receiver_id.upper()}_TELEGRAM_CHAT_ID"
                                    chat_id = os.getenv(chat_id_key)
                                    app = get_telegram_app(receiver_id)
                                    break
            else:
                # Use original sender's chat ID and token
                chat_id_key = f"{sender_id.upper()}_TELEGRAM_CHAT_ID"
                chat_id = os.getenv(chat_id_key)
                app = get_telegram_app(sender_id)
                
            if app and chat_id:
                print(f"Sending message as {sender_id} to chat {chat_id}")
                await app.bot.send_message(chat_id=chat_id, text=message)
            else:
                print(f"Telegram credentials not configured for {'receiver' if sender_id == 'kinos' else 'sender'} {sender_id}")
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
