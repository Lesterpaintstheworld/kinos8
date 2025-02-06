import time
import os
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio
from telegram.ext import ApplicationBuilder
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Telegram credentials from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Initialize Telegram application
application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

class RepositoryChangeHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        asyncio.run(self._handle_file_event("created", event.src_path))

    def on_modified(self, event):
        if event.is_directory:
            return
        asyncio.run(self._handle_file_event("modified", event.src_path))

    def on_deleted(self, event):
        if event.is_directory:
            return
        asyncio.run(self._handle_file_event("deleted", event.src_path))

    async def _handle_file_event(self, event_type, file_path):
        # Convert path to use forward slashes for consistency
        file_path = file_path.replace('\\', '/')
        
        # Skip git and temporary files
        if '.git' in file_path or file_path.endswith('.tmp'):
            return
            
        # Only process created/modified JSON files in data/messages
        if 'data/messages' in file_path and event_type in ['created', 'modified'] and file_path.endswith('.json'):
            try:
                # Wait a brief moment to ensure file is fully written
                await asyncio.sleep(0.1)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.loads(f.read())
                    if 'content' in data:
                        message = f"New message:\n{data['content']}"
                        await self._send_telegram_message(message)
            except Exception as e:
                print(f"Error processing message file {file_path}: {e}")

    async def _send_telegram_message(self, message):
        try:
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                await application.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            else:
                print("Telegram credentials not configured")
        except Exception as e:
            print(f"Error sending Telegram message: {e}")

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
