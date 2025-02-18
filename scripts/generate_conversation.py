import sys
import json
import os
import glob
import codecs
import subprocess
from datetime import datetime
import anthropic
from dotenv import load_dotenv

# Load environment variables from .env file with override
load_dotenv(override=True)

# Get API key and validate
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in .env file")

def load_kinos_context():
    """Load all files from kinos/ directory for context"""
    context = "\nKinOS Context:\n"
    if os.path.exists('kinos'):
        for file in glob.glob('kinos/*.md'):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    filename = os.path.basename(file)
                    context += f"\n=== {filename} ===\n"
                    context += f.read()
                    context += "\n"
            except Exception as e:
                print(f"Error reading {file}: {str(e)}")
    return context

# Force UTF-8 encoding for stdin/stdout/stderr
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
if sys.stdin.encoding != 'utf-8':
    sys.stdin = codecs.getreader('utf-8')(sys.stdin.buffer, 'strict')

# Set default encoding to UTF-8
import locale
locale.getpreferredencoding = lambda: 'UTF-8'

# Set console output encoding to UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Load environment variables
load_dotenv()

# Debug environment variable loading
print("Environment variables loaded:")
print(f"ANTHROPIC_API_KEY present: {bool(os.getenv('ANTHROPIC_API_KEY'))}")

def load_collaboration(collab_id):
    """Load collaboration data from file"""
    collab_files = glob.glob('data/collaborations/*.json')
    for file in collab_files:
        try:
            # Open in binary mode first
            with open(file, 'rb') as f:
                # Decode bytes to string using UTF-8
                content = f.read().decode('utf-8')
                data = json.loads(content)
                if data.get('collaborationId') == collab_id:
                    return data
        except Exception as e:
            print(f"Error reading collaboration file {file}: {str(e)}")
            continue
    return None

def load_messages(collab_id):
    """Load existing messages for the collaboration"""
    messages = []
    message_files = glob.glob('data/messages/*.json')
    for file in message_files:
        try:
            # Skip empty files
            if os.path.getsize(file) == 0:
                print(f"Skipping empty file: {file}")
                continue
                
            # Open in binary mode first
            with open(file, 'rb') as f:
                # Decode bytes to string using UTF-8
                content = f.read().decode('utf-8')
                if not content.strip():
                    print(f"Skipping empty content in file: {file}")
                    continue
                    
                data = json.loads(content)
                if data.get('collaborationId') == collab_id:
                    messages.append(data)
        except json.JSONDecodeError:
            print(f"Skipping invalid JSON in file: {file}")
            continue
        except Exception as e:
            print(f"Error reading message file {file}: {str(e)}")
            continue
    return sorted(messages, key=lambda x: x.get('timestamp', ''))

def generate_message_id(sender_id, timestamp):
    """Generate a unique message ID"""
    date_str = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%Y%m%d-%H%M%S')
    return f"{sender_id}-msg-{date_str}"

def save_message(message_data):
    """Save message to a JSON file"""
    message_id = message_data['messageId']
    filename = f"data/messages/{message_id}.json"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(message_data, f, indent=2, ensure_ascii=False)

def generate_conversation(collab_id, prompt, message_count=1):
    """Generate a conversation using Claude"""
    # Initialize Claude client with global api_key
    client = anthropic.Client(api_key=api_key)
    
    # Load collaboration data
    collab = load_collaboration(collab_id)
    if not collab:
        print(f"Error: Collaboration {collab_id} not found")
        return

    # Initialize Claude client
    client = anthropic.Client(api_key=api_key)
    
    # Generate multiple messages
    for i in range(message_count):
        # Get existing messages for updated context
        existing_messages = load_messages(collab_id)
        
        # Load specifications for this collaboration
        specifications = []
        spec_files = glob.glob('data/specifications/*.json')
        for file in spec_files:
            try:
                # Open in binary mode first
                with open(file, 'rb') as f:
                    # Decode bytes to string using UTF-8
                    content = f.read().decode('utf-8')
                    spec_data = json.loads(content)
                    if spec_data.get('collaborationId') == collab_id:
                        specifications.append(spec_data)
            except Exception as e:
                print(f"Error reading specification file {file}: {str(e)}")
                continue
        
        # Create context for Claude
        context = f"""You are helping generate a conversation between {collab['clientSwarmId']} and {collab['providerSwarmId']}.

{load_kinos_context()}

Collaboration Specifications:
"""
        # Add specifications to context
        for spec in specifications:
            context += f"\nSpecification: {spec.get('title')}\n"
            context += f"Content:\n{spec.get('content')}\n"
            context += "-" * 40 + "\n"

        context += "\nExisting conversation context:\n"
        for msg in existing_messages[-25:]:  # Last 25 messages for context
            context += f"\n{msg['senderId']}: {msg['content']}\n"

        context += f"\nPrompt: {prompt}\n"
        
        try:
            # Generate response using Claude
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": "Generate the next message in this conversation. Return ONLY the message content, no additional formatting or explanation."
                }],
                system=context
            )
            
            if not hasattr(response, 'content') or len(response.content) == 0:
                print("Error: No response content from Claude")
                continue

            # Create message data
            timestamp = datetime.utcnow().isoformat() + 'Z'
            
            # Alternate between senders
            if i % 2 == 0:
                sender_id = collab['providerSwarmId']
                receiver_id = collab['clientSwarmId']
            else:
                sender_id = collab['clientSwarmId']
                receiver_id = collab['providerSwarmId']
                
            message_data = {
                "collaborationId": collab_id,
                "senderId": sender_id,
                "receiverId": receiver_id,
                "content": response.content[0].text.strip(),
                "timestamp": timestamp,
                "messageId": generate_message_id(sender_id, timestamp)
            }
            
            # Save the message
            save_message(message_data)
            print(f"\nGenerated message {i+1}/{message_count} saved as {message_data['messageId']}.json")
            print("\nMessage content:")
            print("-" * 50)
            print(message_data['content'])
            print("-" * 50)
            
        except Exception as e:
            print(f"Error generating message {i+1}: {str(e)}")

def main():
    if len(sys.argv) < 4:
        print("Usage: python generate_conversation.py <collaboration_id> <prompt> <message_count>")
        return
    
    collab_id = sys.argv[1]
    prompt = sys.argv[2]
    message_count = int(sys.argv[3])
    
    generate_conversation(collab_id, prompt, message_count)

if __name__ == "__main__":
    main()
