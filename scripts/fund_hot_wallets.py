import os
import json
import glob
import codecs
import sys
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.transaction import Transaction
from solders.system_program import transfer, TransferParams
from solders.pubkey import Pubkey
from spl.token.instructions import transfer as spl_transfer
import base58
from dotenv import load_dotenv

# Force UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

load_dotenv()

def load_treasury_wallet():
    """Load encrypted treasury wallet"""
    try:
        # Load encrypted key
        with open('secure/treasury_wallet.enc', 'r') as f:
            encrypted_key = f.read()
            
        # Create encryption key from environment variables
        salt = os.getenv('WALLET_SALT').encode()
        password = (
            os.getenv('WALLET_SECRET_1') + 
            os.getenv('WALLET_SECRET_2')
        ).encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        
        # Decrypt private key
        f = Fernet(key)
        private_key = f.decrypt(encrypted_key.encode()).decode()
        
        return Keypair.from_bytes(base58.b58decode(private_key))
    except Exception as e:
        print(f"Error loading treasury wallet: {e}")
        return None

def load_swarms_with_hot_wallets():
    """Load all swarms that have hot wallets"""
    swarms = {}
    swarm_files = glob.glob('data/swarms/*.json')
    for file in swarm_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                swarm = json.load(f)
                if 'hotWallet' in swarm:
                    swarms[swarm['swarmId']] = swarm
        except Exception as e:
            print(f"Error loading {file}: {str(e)}")
    return swarms

def fund_hot_wallets():
    """Fund hot wallets with initial SOL"""
    # Load treasury wallet
    treasury = load_treasury_wallet()
    if not treasury:
        print("Failed to load treasury wallet")
        return
        
    print(f"Loaded treasury wallet: {treasury.pubkey()}")
    
    # Load all swarms with hot wallets
    swarms = load_swarms_with_hot_wallets()
    print(f"\nFound {len(swarms)} hot wallets to fund")
    
    # Initialize Solana client with Helius RPC
    helius_url = os.getenv('NEXT_PUBLIC_HELIUS_RPC_URL')
    if not helius_url:
        print("Error: NEXT_PUBLIC_HELIUS_RPC_URL not found in environment variables")
        return
        
    client = Client(helius_url)
    print(f"Connected to Helius RPC endpoint")
    
    for swarm_id, swarm in swarms.items():
        hot_wallet = swarm['hotWallet']
        print(f"\nProcessing {swarm_id}")
        print(f"Hot wallet: {hot_wallet}")
        
        try:
            # Get recent blockhash using the correct method
            recent_blockhash = client.get_latest_blockhash()['result']['value']['blockhash']
            
            # Create transfer instruction
            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=treasury.pubkey(),
                    to_pubkey=Pubkey.from_string(hot_wallet),
                    lamports=10000000  # 0.01 SOL
                )
            )
            
            # Create transaction
            tx = Transaction()
            tx.recent_blockhash = recent_blockhash
            tx.add(transfer_ix)
            
            print("Sending 0.01 SOL...")
            # Sign and send transaction
            result = client.send_transaction(tx, treasury)
            print(f"SOL transfer signature: {result['result']}")
            print(f"Successfully funded {swarm_id} hot wallet")
            
        except Exception as e:
            print(f"Error funding {swarm_id}: {e}")
            import traceback
            print("Full error traceback:")
            print(traceback.format_exc())

def main():
    print("Starting hot wallet funding process...")
    fund_hot_wallets()
    print("\nFunding process complete!")

if __name__ == "__main__":
    main()
