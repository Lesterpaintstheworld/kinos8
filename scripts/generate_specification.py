import sys
import json
import os
import glob
import codecs
import subprocess
from datetime import datetime
import anthropic
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

def load_collaboration(collab_id):
    """Load collaboration data and related information"""
    try:
        # Load collaboration
        collab_files = glob.glob('data/collaborations/*.json')
        collab_data = None
        for file in collab_files:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('collaborationId') == collab_id:
                    collab_data = data
                    break
        
        if not collab_data:
            raise Exception(f"Collaboration {collab_id} not found")

        # Load related messages
        messages = []
        message_files = glob.glob('data/messages/*.json')
        for file in message_files:
            with open(file, 'r') as f:
                data = json.load(f)
                if data.get('collaborationId') == collab_id:
                    messages.append(data)
        
        # Load related specifications
        specs = []
        spec_files = glob.glob('data/specifications/*.json')
        for file in spec_files:
            with open(file, 'r') as f:
                data = json.load(f)
                if data.get('collaborationId') == collab_id:
                    specs.append(data)
        
        return collab_data, messages, specs
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, [], []


def git_operations(spec_id):
    """Add, commit and push the new specification file"""
    try:
        # Git add
        subprocess.run(["git", "add", f"data/specifications/{spec_id}.json"], check=True)
        
        # Git commit
        commit_message = f"Added specification {spec_id}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        
        # Git push
        subprocess.run(["git", "push"], check=True)
        
        print("\nSpecification file committed and pushed to repository")
        
    except subprocess.CalledProcessError as e:
        print(f"Error in git operations: {e}")
        raise

def generate_specification(collab_id, topic):
    """Generate a specification document using Claude"""
    collab, messages, existing_specs = load_collaboration(collab_id)
    if not collab:
        print(f"Could not find collaboration {collab_id}")
        return

    client = anthropic.Client(
        api_key=os.getenv('ANTHROPIC_API_KEY')
    )
    
    # Build context
    context = f"""You are helping generate a detailed technical specification document.

Collaboration Context:
- Between: {collab.get('clientSwarmId')} and {collab.get('providerSwarmId')}
- Description: {collab.get('description')}

Recent Messages:
"""
    # Add last 25 messages for context
    for msg in sorted(messages, key=lambda x: x.get('timestamp', ''))[-25:]:
        context += f"- From {msg.get('senderId')} to {msg.get('receiverId')}: {msg.get('content')}\n"

    context += "\nExisting Specifications:\n"
    for spec in existing_specs:
        context += f"- {spec.get('title')}: {spec.get('content')[:200]}...\n"

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": f"Generate a detailed technical specification document for: {topic}\n\nThe specification should include:\n1. Overview\n2. Requirements\n3. Technical Details\n4. Implementation Plan\n5. Success Criteria"
            }],
            system=context
        )
        
        if hasattr(response, 'content') and len(response.content) > 0:
            spec_content = response.content[0].text
            
            # Create specification data
            timestamp = datetime.utcnow().isoformat() + 'Z'
            spec_id = f"spec-{collab_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            specification = {
                "specificationId": spec_id,
                "collaborationId": collab_id,
                "title": topic,
                "content": spec_content
            }
            
            # Save specification with UTF-8 encoding
            filename = f"data/specifications/{spec_id}.json"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(specification, f, indent=2, ensure_ascii=False)
            
            print(f"\nSpecification generated and saved as {filename}")
            print("\nSpecification content:")
            print("=" * 50)
            try:
                print(spec_content.encode('utf-8').decode('utf-8'))
            except UnicodeEncodeError:
                print("Note: Some characters could not be displayed in console")
                print(spec_content.encode('ascii', 'replace').decode('ascii'))
            print("=" * 50)
            
            # Git operations
            git_operations(spec_id)
            
            return specification
            
    except Exception as e:
        print(f"Error generating specification: {e}")
        return None

def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_specification.py <collaboration_id> <topic>")
        return
        
    collab_id = sys.argv[1]
    topic = ' '.join(sys.argv[2:])
    
    print(f"Generating specification for collaboration {collab_id}")
    print(f"Topic: {topic}")
    
    specification = generate_specification(collab_id, topic)
    if specification:
        print(f"\nSpecification {specification['specificationId']} generated successfully")

if __name__ == '__main__':
    main()
