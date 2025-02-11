import os
import sys
import glob
import json
import codecs
from datetime import datetime
import anthropic
from telegram.ext import ApplicationBuilder
from dotenv import load_dotenv

# Force UTF-8 encoding for stdin/stdout/stderr
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
if sys.stdin.encoding != 'utf-8':
    sys.stdin = codecs.getreader('utf-8')(sys.stdin.buffer, 'strict')

# Set default encoding to UTF-8
import locale
locale.getpreferredencoding = lambda: 'UTF-8'

# Load environment variables
load_dotenv()

def load_json_files(pattern, limit):
    """Load most recent JSON files based on pattern and limit"""
    files = glob.glob(pattern)
    # Sort files by modification time, most recent first
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    results = []
    for file in files[:limit]:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results.append(data)
        except Exception as e:
            print(f"Error loading {file}: {e}")
    
    return results

def build_system_prompt():
    """Build system prompt from recent data"""
    # Load swarm data
    with open('data/swarms/kinos.json', 'r') as f:
        kinos_data = json.load(f)
    with open('data/swarms/xforge.json', 'r') as f:
        xforge_data = json.load(f)
    
    # Load all services
    services = []
    service_files = glob.glob('data/services/*.json')
    for file in service_files:
        with open(file, 'r') as f:
            services.append(json.load(f))
    
    # Load messages between kinos and xforge
    messages = []
    message_files = glob.glob('data/messages/*.json')
    for file in message_files:
        with open(file, 'r') as f:
            data = json.load(f)
            if ((data.get('senderId') == 'kinos' and data.get('receiverId') == 'xforge') or
                (data.get('senderId') == 'xforge' and data.get('receiverId') == 'kinos')):
                messages.append(data)
    
    # Load all news
    news = []
    news_files = glob.glob('data/news/*.json')
    for file in news_files:
        with open(file, 'r') as f:
            news.append(json.load(f))
    
    # Build prompt
    prompt = "You are a helpful AI assistant tasked with creating a recap of recent UBC ecosystem activities. Here's the relevant data:\n\n"
    
    # Add swarm information
    prompt += "KinOS Swarm:\n"
    prompt += f"Description: {kinos_data.get('shortDescription')}\n"
    prompt += f"Weekly Revenue: {kinos_data.get('weeklyRevenue')} $COMPUTE\n\n"
    
    prompt += "XForge Swarm:\n"
    prompt += f"Description: {xforge_data.get('shortDescription')}\n"
    prompt += f"Weekly Revenue: {xforge_data.get('weeklyRevenue')} $COMPUTE\n\n"
    
    # Add all services
    prompt += "Available Services:\n"
    for service in services:
        prompt += f"- {service.get('name')}: {service.get('description')}\n"
    
    # Add messages between swarms
    prompt += "\nRecent Communications:\n"
    for msg in sorted(messages, key=lambda x: x.get('timestamp', ''), reverse=True):
        prompt += f"- From {msg.get('senderId')} to {msg.get('receiverId')}: {msg.get('content')}\n"
    
    # Add all news
    prompt += "\nRecent News:\n"
    for news_item in sorted(news, key=lambda x: x.get('timestamp', ''), reverse=True):
        prompt += f"- {news_item.get('title', 'Untitled')}: {news_item.get('content')}\n"
    
    return prompt

def generate_recap():
    """Generate recap using Anthropic's Claude"""
    client = anthropic.Client(
        api_key=os.getenv('ANTHROPIC_API_KEY')
    )
    
    system_prompt = build_system_prompt()
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # don't change this value!!!!!
            max_tokens=2000,
            system=system_prompt,  # System prompt goes here as a parameter
            messages=[
                {
                    "role": "user", 
                    "content": """Create a concise but informative recap of recent activities in the UBC ecosystem. 
                    Focus on key developments, collaborations, and important messages.
                    Format it in a clear, engaging way suitable for a Telegram announcement.
                    Keep it under 2000 characters."""
                }
            ]
        )
        
        if hasattr(response, 'content') and len(response.content) > 0:
            return response.content[0].text
        else:
            raise Exception("No content in response")
            
    except Exception as e:
        print(f"Error generating recap with Claude: {str(e)}")
        raise

async def send_telegram_message(recap_text):
    """Send recap to Telegram main chat"""
    token = os.getenv('KINKONG_TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('MAIN_TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        raise ValueError("Telegram credentials not properly configured")
    
    app = ApplicationBuilder().token(token).build()
    
    try:
        await app.bot.send_message(
            chat_id=chat_id,
            text=f"🔄 UBC Ecosystem Recap\n\n{recap_text}\n\n#UBCRecap"
        )
        print("Recap sent successfully to Telegram")
    except Exception as e:
        print(f"Error sending to Telegram: {e}")
    finally:
        await app.shutdown()

def main():
    try:
        # Generate recap
        print("Generating recap...")
        recap = generate_recap()
        
        # Send to Telegram
        print("Sending to Telegram...")
        import asyncio
        asyncio.run(send_telegram_message(recap))
        
        print("Recap process completed successfully!")
        
    except Exception as e:
        print(f"Error in recap process: {str(e)}")
        import traceback
        print("\nFull error traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
