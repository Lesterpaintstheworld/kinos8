import os
import glob
import json
from datetime import datetime
import anthropic
from telegram.ext import ApplicationBuilder
from dotenv import load_dotenv

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
    messages = load_json_files('data/messages/*.json', 100)
    collaborations = load_json_files('data/collaborations/*.json', 50)
    swarms = load_json_files('data/swarms/*.json', 50)
    
    prompt = "You are a helpful AI assistant tasked with creating a recap of recent UBC ecosystem activities. "
    prompt += "Use the following data to create a concise, engaging summary:\n\n"
    
    # Add messages context
    prompt += "Recent Messages:\n"
    for msg in messages:
        prompt += f"- From {msg.get('senderId')} to {msg.get('receiverId')}: {msg.get('content')}\n"
    
    # Add collaborations context
    prompt += "\nActive Collaborations:\n"
    for collab in collaborations:
        prompt += f"- {collab.get('clientSwarmId')} with {collab.get('providerSwarmId')}: {collab.get('description')}\n"
    
    # Add swarms context
    prompt += "\nSwarm Information:\n"
    for swarm in swarms:
        prompt += f"- {swarm.get('name')}: {swarm.get('shortDescription')}\n"
    
    return prompt

def generate_recap():
    """Generate recap using Anthropic's Claude"""
    client = anthropic.Client(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    system_prompt = build_system_prompt()
    
    user_prompt = """Create a concise but informative recap of recent activities in the UBC ecosystem. 
    Focus on key developments, collaborations, and important messages.
    Format it in a clear, engaging way suitable for a Telegram announcement.
    Include relevant numbers and metrics where available.
    Keep it under 2000 characters."""
    
    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=2000,
        temperature=0.7,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )
    
    return message.content

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
        print(f"Error in recap process: {e}")

if __name__ == "__main__":
    main()
