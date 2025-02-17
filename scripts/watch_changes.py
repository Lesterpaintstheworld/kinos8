import time
import os
import sys
import json
import glob
import codecs
import subprocess
import logging
from typing import Optional, Dict, Any
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

def safe_read_json(file_path: str, max_retries: int = 3, retry_delay: float = 0.5) -> Dict[str, Any]:
    """Safely read and parse JSON file with improved retry logic"""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    raise ValueError("Empty file")
                return json.loads(content)
        except (json.JSONDecodeError, IOError, ValueError) as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            
    raise ValueError(f"Failed to read {file_path} after {max_retries} attempts: {last_error}")

def is_file_ready(file_path: str, timeout: int = 5, check_interval: float = 0.1) -> bool:
    """
    Check if file is completely written and accessible with improved retry logic.
    
    Args:
        file_path: Path to the file to check
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
    """
    start_time = time.time()
    
    # Skip only git and temp files
    if '.git' in file_path or '.tmp' in file_path:
        return False
        
    while time.time() - start_time < timeout:
        try:
            # Check if file exists and is not empty
            if not os.path.exists(file_path):
                time.sleep(check_interval)
                continue
                
            # Get file size
            size1 = os.path.getsize(file_path)
            time.sleep(check_interval)  # Wait briefly
            size2 = os.path.getsize(file_path)
            
            # If size hasn't changed and file is not empty
            if size1 == size2 and size1 > 0:
                # Try to read and parse if it's a JSON file
                if file_path.endswith('.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json.loads(f.read())
                return True
                
        except (IOError, json.JSONDecodeError):
            time.sleep(check_interval)
            continue
            
    logging.warning(f"File not ready after {timeout}s: {file_path}")
    return False

# Initialize Airtable API
api = Api(AIRTABLE_API_KEY)

# Cache for Telegram applications and event loops
telegram_apps: Dict[str, Any] = {}
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

class FileLock:
    def __init__(self):
        self._locks = {}
        self._lock = asyncio.Lock()
    
    async def acquire(self, file_path):
        async with self._lock:
            if file_path not in self._locks:
                self._locks[file_path] = asyncio.Lock()
        return await self._locks[file_path].acquire()
    
    async def release(self, file_path):
        if file_path in self._locks:
            self._locks[file_path].release()

class RepositoryChangeHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.processed_messages = set()  # Track processed messages
        self.file_lock = FileLock()

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
            elif 'data/thoughts' in file_path:
                table = api.table(BASE_ID, 'Thoughts')
                id_field = 'thoughtId'
            else:
                return
            
            # Read the file with retry mechanism
            data = safe_read_json(file_path)
            
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
        # Convert path to use forward slashes and normalize structure
        file_path = file_path.replace('\\', '/')
        if file_path.startswith('./'):
            file_path = file_path[2:]
        
        # Add debug logging
        print(f"Detected {event_type} event for: {file_path}")
        print(f"DEBUG: Processing file: {file_path}")
        print(f"DEBUG: Event type: {event_type}")

        # Skip non-relevant files early
        if any(skip in file_path for skip in ['.git', '.aider', '.tmp']):
            return
            
        # Only process certain file types
        if not any(f"data/{d}" in file_path for d in ['messages', 'news', 'thoughts', 'specifications',
                                                       'deliverables', 'collaborations', 'swarms', 'services',
                                                       'missions']) and 'kinos' not in file_path:
            print(f"Skipping non-data file: {file_path}")
            return
            
        # Wait for file to be ready with increased timeout for larger files
        timeout = 10 if any(x in file_path for x in ['specifications', 'deliverables', 'thoughts']) else 5
        max_attempts = 3
        
        for attempt in range(max_attempts):
            if is_file_ready(file_path, timeout=timeout):
                print(f"File is ready after attempt {attempt + 1}: {file_path}")
                break
            if attempt == max_attempts - 1:
                print(f"File not ready after {max_attempts} attempts: {file_path}")
                return
            await asyncio.sleep(1)  # Wait between attempts
        
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
            
        # Only process new JSON files for notifications, regardless of event type
        if file_path.endswith('.json') and file_path not in self.processed_messages:
            # Handle messages
            if 'data/messages' in file_path:
                print(f"DEBUG: Processing message file")
                try:
                    data = safe_read_json(file_path)
                    print(f"DEBUG: Message data loaded: {data.get('messageId')}")
                    if 'content' in data and 'senderId' in data and 'messageId' in data:
                        print(f"DEBUG: Required fields present")
                        self.processed_messages.add(file_path)
                        current_time = time.time()
                        if hasattr(self, 'last_message_time'):
                            time_since_last = current_time - self.last_message_time
                            if time_since_last < 2:
                                await asyncio.sleep(2 - time_since_last)
                    
                        message = f"{data['content']}"
                        await self._send_telegram_message(message, data['senderId'])
                        self.last_message_time = time.time()
                        print(f"Processed new message {data['messageId']}")
                except Exception as e:
                    print(f"Error processing message file {file_path}: {e}")
                
            # Handle news
            elif 'data/news' in file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.loads(f.read())
                        if 'content' in data and 'swarmId' in data:
                            message = f"News: {data['content']}"
                            await self._send_telegram_message(message, data['swarmId'])
                            self.last_message_time = time.time()
                            print(f"Processed new news from {data['swarmId']}")
                except Exception as e:
                    print(f"Error processing news file {file_path}: {e}")
                
            # Handle specifications
            elif 'data/specifications' in file_path:
                try:
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
                                content_preview = data.get('content', '')[:200] + '...' if len(data.get('content', '')) > 200 else data.get('content', '')
                                message = (f"📋 New Specification\n\n"
                                         f"Title: {data.get('title')}\n"
                                         f"Created: {data.get('createdAt')}\n\n"
                                         f"Preview:\n{content_preview}\n\n"
                                         f"View full specification at:\n"
                                         f"https://swarms.universalbasiccompute.ai/specifications/{data['specificationId']}")
                                await self._send_telegram_message(message, client_swarm_id)
                                print(f"Sent notification for new specification to {client_swarm_id}")
                except Exception as e:
                    print(f"Error processing specification file {file_path}: {e}")
                
            # Handle deliverables
            elif 'data/deliverables' in file_path:
                try:
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
                                content_preview = data.get('content', '')[:250] + '...' if len(data.get('content', '')) > 200 else data.get('content', '')
                                message = (f"📦 New Deliverable\n\n"
                                         f"Title: {data.get('title')}\n"
                                         f"Preview:\n{content_preview}\n\n"
                                         f"View full deliverable at:\n"
                                         f"https://swarms.universalbasiccompute.ai/deliverables/{data['deliverableId']}")
                                await self._send_telegram_message(message, client_swarm_id)
                                print(f"Sent notification for new deliverable to {client_swarm_id}")
                except Exception as e:
                    print(f"Error processing deliverable file {file_path}: {e}")
                
            # Handle thoughts
            elif 'data/thoughts' in file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'thoughtId' in data and 'swarmId' in data:
                            content_preview = data.get('content', '')[:1000] + '...' if len(data.get('content', '')) > 200 else data.get('content', '')
                            message = (f"💭 New Thought from {data['swarmId']}\n\n"
                                     f"{content_preview}\n\n")
                            await self._send_telegram_message(message, data['swarmId'])
                            print(f"Sent notification for new thought from {data['swarmId']}")
                except Exception as e:
                    print(f"Error processing thought file {file_path}: {e}")
            
            # Handle missions
            elif 'data/missions' in file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'missionId' in data and 'leadSwarm' in data:
                            content_preview = data.get('description', '')[:200] + '...' if len(data.get('description', '')) > 200 else data.get('description', '')
                            message = (f"🎯 New Mission\n\n"
                                     f"Title: {data.get('title')}\n"
                                     f"Priority: {data.get('priority')}\n"
                                     f"Status: {data.get('status')}\n\n"
                                     f"Description:\n{content_preview}\n\n"
                                     f"View full mission at:\n"
                                     f"https://swarms.universalbasiccompute.ai/missions/{data['missionId']}")
                            await self._send_telegram_message(message, data['leadSwarm'])
                            print(f"Sent notification for new mission to {data['leadSwarm']}")
                except Exception as e:
                    print(f"Error processing mission file {file_path}: {e}")

    async def _send_telegram_message(self, message, sender_id):
        try:
            print(f"DEBUG: Starting Telegram send process")
            print(f"DEBUG: Sender ID: {sender_id}")
            print(f"DEBUG: Message: {message[:100]}...")  # First 100 chars
            
            # Check environment variables
            main_chat = os.getenv('MAIN_TELEGRAM_CHAT_ID')
            bot_token = os.getenv(f'{sender_id.upper()}_TELEGRAM_BOT_TOKEN')
            print(f"DEBUG: Main chat ID exists: {bool(main_chat)}")
            print(f"DEBUG: Bot token exists for {sender_id}: {bool(bot_token)}")
            
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

            # If client found, get their telegram chat ID from their swarm file
            chat_id = None
            if client_swarm_id:
                swarm_file = f'data/swarms/{client_swarm_id}.json'
                if os.path.exists(swarm_file):
                    with open(swarm_file, 'r', encoding='utf-8') as f:
                        swarm_data = json.load(f)
                        if swarm_data.get('telegramChatId'):
                            chat_id = int(swarm_data['telegramChatId'])
                            logging.info(f"Using client {client_swarm_id}'s telegram chat: {chat_id}")

            # Fallback to main chat if no client chat found
            if not chat_id:
                chat_id = int(os.getenv('MAIN_TELEGRAM_CHAT_ID'))
                logging.info(f"Using main chat ID for message from {sender_id}")
            
            print(f"DEBUG: Using chat ID: {chat_id}")
            
            # Get app
            app = get_telegram_app(sender_id)
            print(f"DEBUG: Telegram app created: {bool(app)}")
            
            if app and chat_id:
                print(f"DEBUG: Attempting to send message...")
                await app.bot.send_message(chat_id=chat_id, text=message)
                print(f"DEBUG: Message sent successfully")
            else:
                print(f"DEBUG: Failed to send - Missing {'app' if not app else 'chat_id'}")
                print(f"DEBUG: Sender: {sender_id}")
                print(f"DEBUG: Chat ID: {chat_id}")
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            print(f"Sender: {sender_id}")
            print(f"Chat ID: {chat_id if 'chat_id' in locals() else 'Not found'}")

def main():
    # Get all paths to watch
    def get_watch_paths():
        paths = []
        base_dirs = ["data", "kinos"]
        
        # Add data subdirectories
        data_dirs = ["messages", "news", "thoughts", "specifications", 
                    "deliverables", "collaborations", "swarms", "services",
                    "missions"]
        for dir in data_dirs:
            path = os.path.join("data", dir)
            if os.path.exists(path):
                paths.append(path)
                
        # Add kinos directory if it exists
        if os.path.exists("kinos"):
            paths.append("kinos")
            
        return paths

    # Get paths and create handler/observer    
    paths = get_watch_paths()
    event_handler = RepositoryChangeHandler()
    observer = Observer()
    
    # Schedule watching for each path
    for path in paths:
        normalized_path = path.replace(os.sep, '/')
        if os.path.exists(path):
            observer.schedule(event_handler, path, recursive=False)
            print(f"Watching {normalized_path} for changes...")
        else:
            print(f"Warning: Path does not exist: {normalized_path}")
    
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
