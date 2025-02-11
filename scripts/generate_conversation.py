import sys
import json
import os
import glob
from datetime import datetime
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def load_collaboration(collab_id):
    """Load collaboration data from file"""
    collab_files = glob.glob('data/collaborations/*.json')
    for file in collab_files:
        with open(file, 'r') as f:
            data = json.load(f)
            if data.get('collaborationId') == collab_id:
                return data
    return None

def load_messages(collab_id):
    """Load existing messages for the collaboration"""
    messages = []
    message_files = glob.glob('data/messages/*.json')
    for file in message_files:
        with open(file, 'r') as f:
            data = json.load(f)
            if data.get('collaborationId') == collab_id:
                messages.append(data)
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
    with open(filename, 'w') as f:
        json.dump(message_data, f, indent=2)

def generate_conversation(collab_id, prompt):
    """Generate a conversation using Claude"""
    # Load collaboration data
    collab = load_collaboration(collab_id)
    if not collab:
        print(f"Error: Collaboration {collab_id} not found")
        return

    # Get existing messages
    existing_messages = load_messages(collab_id)
    
    # Create context for Claude
    context = f"""You are helping generate a conversation between {collab['clientSwarmId']} and {collab['providerSwarmId']}.

Existing conversation context:
"""
    
    for msg in existing_messages[-5:]:  # Last 5 messages for context
        context += f"\n{msg['senderId']}: {msg['content']}\n"

    context += f"\nPrompt: {prompt}\n"
    
    # Initialize Claude client
    client = anthropic.Client(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    try:
        # Generate response using Claude
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=2000,
            system=context,
            messages=[{
                "role": "user",
                "content": "Generate the next message in this conversation. Return ONLY the message content, no additional formatting or explanation."
            }]
        )
        
        if not hasattr(response, 'content') or len(response.content) == 0:
            print("Error: No response content from Claude")
            return

        # Create message data
        timestamp = datetime.utcnow().isoformat() + 'Z'
        message_data = {
            "collaborationId": collab_id,
            "senderId": collab['providerSwarmId'],
            "receiverId": collab['clientSwarmId'],
            "content": response.content[0].text.strip(),
            "timestamp": timestamp,
            "messageId": generate_message_id(collab['providerSwarmId'], timestamp)
        }
        
        # Save the message
        save_message(message_data)
        print(f"\nGenerated message saved as {message_data['messageId']}.json")
        print("\nMessage content:")
        print("-" * 50)
        print(message_data['content'])
        print("-" * 50)
        
    except Exception as e:
        print(f"Error generating conversation: {str(e)}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_conversation.py <collaboration_id> <prompt>")
        return
    
    collab_id = sys.argv[1]
    prompt = ' '.join(sys.argv[2:])
    
    generate_conversation(collab_id, prompt)

if __name__ == "__main__":
    main()
