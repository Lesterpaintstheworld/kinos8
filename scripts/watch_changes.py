import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import telegram
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Telegram credentials from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Initialize Telegram bot
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

class RepositoryChangeHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        self._handle_file_event("created", event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle_file_event("modified", event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        self._handle_file_event("deleted", event.src_path)

    def _handle_file_event(self, event_type, file_path):
        # Convert path to use forward slashes for consistency
        file_path = file_path.replace('\\', '/')
        
        # Handle messages
        if 'data/messages' in file_path:
            message = f"Message file {os.path.basename(file_path)} was {event_type}"
            self._send_telegram_message(message)
            
        # Handle collaborations
        elif 'data/collaborations' in file_path:
            message = f"Collaboration {os.path.basename(file_path)} was {event_type}"
            self._send_telegram_message(message)
            
        # Add more handlers for other directories as needed
        # elif 'data/specifications' in file_path:
        #     ...

    def _send_telegram_message(self, message):
        try:
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
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
