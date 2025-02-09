import json
import glob
import os

def load_collaborations():
    """Load all collaboration data into a dictionary keyed by collaborationId"""
    collaborations = {}
    collab_files = glob.glob('data/collaborations/*.json')
    
    for file_path in collab_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'collaborationId' in data:
                    collaborations[data['collaborationId']] = data
        except Exception as e:
            print(f"Error loading collaboration file {file_path}: {e}")
    
    return collaborations

def determine_receiver(collaboration, sender_id):
    """Determine the receiver based on collaboration and sender"""
    if sender_id == collaboration['clientSwarmId']:
        return collaboration['providerSwarmId']
    elif sender_id == collaboration['providerSwarmId']:
        return collaboration['clientSwarmId']
    else:
        print(f"Warning: sender {sender_id} not found in collaboration {collaboration['collaborationId']}")
        return None

def update_messages():
    """Update all message files with receiverId"""
    collaborations = load_collaborations()
    message_files = glob.glob('data/messages/*.json')
    
    updated_count = 0
    skipped_count = 0
    
    for file_path in message_files:
        try:
            # Load message
            with open(file_path, 'r', encoding='utf-8') as f:
                message = json.load(f)
            
            # Skip if no collaboration ID or sender ID
            if 'collaborationId' not in message or 'senderId' not in message:
                print(f"Skipping {file_path} - missing required fields")
                skipped_count += 1
                continue
            
            # Get collaboration
            collab = collaborations.get(message['collaborationId'])
            if not collab:
                print(f"Skipping {file_path} - collaboration {message['collaborationId']} not found")
                skipped_count += 1
                continue
            
            # Determine receiver
            receiver_id = determine_receiver(collab, message['senderId'])
            if not receiver_id:
                skipped_count += 1
                continue
            
            # Add receiverId
            message['receiverId'] = receiver_id
            
            # Save updated message
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(message, f, indent=2)
            
            print(f"Updated {file_path}")
            updated_count += 1
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            skipped_count += 1
    
    print(f"\nCompleted:")
    print(f"  - Updated: {updated_count}")
    print(f"  - Skipped: {skipped_count}")

def main():
    print("Adding receiverId to messages...")
    update_messages()

if __name__ == '__main__':
    main()
