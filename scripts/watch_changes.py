import time
import os
import time
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
        
        # Skip git and temporary files
        if '.git' in file_path or file_path.endswith('.tmp'):
            return
            
        # Handle different data directories
        if 'data/' in file_path:
            category = file_path.split('data/')[1].split('/')[0]
            filename = os.path.basename(file_path)
            
            message = f"📝 {category.title()}\n"
            message += f"File: {filename}\n"
            message += f"Action: {event_type.title()}\n"
            message += f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Add specific emojis based on category
            if category == 'messages':
                message = "💬 " + message
            elif category == 'collaborations':
                message = "🤝 " + message
            elif category == 'specifications':
                message = "📋 " + message
            elif category == 'deliverables':
                message = "📦 " + message
            elif category == 'news':
                message = "📰 " + message
            elif category == 'services':
                message = "🛠️ " + message
            elif category == 'swarms':
                message = "🐝 " + message
            elif category == 'validations':
                message = "✅ " + message
                
            self._send_telegram_message(message)

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
