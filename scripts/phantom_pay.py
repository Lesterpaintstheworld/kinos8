import sys
import json
import os
import glob
import codecs
from datetime import datetime
import webbrowser
from dotenv import load_dotenv

# Force UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
if sys.stdin.encoding != 'utf-8':
    sys.stdin = codecs.getreader('utf-8')(sys.stdin.buffer, 'strict')

# Set default encoding to UTF-8
import locale
locale.getpreferredencoding = lambda: 'UTF-8'

def load_swarm(swarm_id):
    """Load swarm data"""
    try:
        with open(f'data/swarms/{swarm_id}.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading swarm {swarm_id}: {e}")
        return None

def load_collaboration(collab_id):
    """Load collaboration data"""
    collab_files = glob.glob('data/collaborations/*.json')
    for file in collab_files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data.get('collaborationId') == collab_id:
                return data
    return None

def generate_phantom_url(from_wallet, to_wallet, amount, memo):
    """Generate Phantom payment URL"""
    base_url = "https://phantom.app/ul/v1/transfer"
    params = {
        "from": from_wallet,
        "to": to_wallet,
        "amount": str(amount),
        "memo": memo,
        "splToken": os.getenv('COMPUTE_TOKEN_ADDRESS')  # Get $COMPUTE token address from env
    }
    
    # Build URL with parameters
    url_params = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{url_params}"

def process_payment(client_id, collab_id):
    """Process payment for a collaboration"""
    # Load client swarm data
    client_swarm = load_swarm(client_id)
    if not client_swarm:
        print(f"Error: Client swarm {client_id} not found")
        return
        
    # Load collaboration data
    collab = load_collaboration(collab_id)
    if not collab:
        print(f"Error: Collaboration {collab_id} not found")
        return
        
    # Load provider swarm data
    provider_swarm = load_swarm(collab['providerSwarmId'])
    if not provider_swarm:
        print(f"Error: Provider swarm {collab['providerSwarmId']} not found")
        return
    
    # Get payment details
    amount = collab['price']
    from_wallet = client_swarm['wallet']
    to_wallet = provider_swarm['wallet']
    memo = f"Payment for collaboration {collab_id}"
    
    # Generate payment URL
    payment_url = generate_phantom_url(from_wallet, to_wallet, amount, memo)
    
    print(f"\nProcessing payment for collaboration {collab_id}")
    print(f"From: {client_id} ({from_wallet})")
    print(f"To: {collab['providerSwarmId']} ({to_wallet})")
    print(f"Amount: {amount:,} $COMPUTE")
    print(f"\nOpening Phantom wallet...")
    
    # Open payment URL in default browser
    webbrowser.open(payment_url)
    
    print("\nPlease complete the transaction in your Phantom wallet.")
    print("Note: Make sure you have the Phantom wallet browser extension installed.")

def main():
    if len(sys.argv) < 3:
        print("Usage: python phantom_pay.py <client_swarm_id> <collaboration_id>")
        return
        
    client_id = sys.argv[1]
    collab_id = sys.argv[2]
    
    process_payment(client_id, collab_id)

if __name__ == "__main__":
    main()
