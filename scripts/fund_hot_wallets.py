import os
import json
import glob
import codecs
import sys
import base64
import time
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from solders.keypair import Keypair
from solana.rpc.api import Client
from solana.transaction import Transaction
from solders.pubkey import Pubkey
from spl.token.instructions import TransferParams, transfer, create_associated_token_account, get_associated_token_address
from spl.token.constants import TOKEN_PROGRAM_ID
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
    """Fund hot wallets with initial COMPUTE"""
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
    compute_token_mint = Pubkey.from_string(os.getenv('COMPUTE_TOKEN_ADDRESS'))
    print(f"Connected to Helius RPC endpoint")
    
    for swarm_id, swarm in swarms.items():
        hot_wallet = swarm['hotWallet']
        print(f"\nProcessing {swarm_id}")
        print(f"Hot wallet: {hot_wallet}")
        
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                # Get recent blockhash
                print("Getting recent blockhash...")
                blockhash_response = client.get_latest_blockhash()
                recent_blockhash = blockhash_response.value.blockhash
                print(f"Got blockhash: {recent_blockhash}")
                
                # Get or create token account
                print("Creating/checking token account...")
                hot_wallet_pubkey = Pubkey.from_string(hot_wallet)
                token_account = get_associated_token_address(hot_wallet_pubkey, compute_token_mint)
                
                # Create token account if it doesn't exist
                create_account_ix = create_associated_token_account(
                    payer=treasury.pubkey(),
                    owner=hot_wallet_pubkey,
                    mint=compute_token_mint
                )
                
                # Create transfer instruction
                print("Creating COMPUTE transfer instruction...")
                transfer_params = TransferParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=get_associated_token_address(treasury.pubkey(), compute_token_mint),
                    dest=token_account,
                    owner=treasury.pubkey(),
                    amount=1000000,  # 1M COMPUTE
                    signers=[]
                )
                
                # Create transaction with both instructions
                tx = Transaction()
                tx.add(create_account_ix)  # Add create account instruction
                tx.add(transfer(transfer_params))  # Add transfer instruction
                tx.recent_blockhash = recent_blockhash
                
                print("Signing and sending transaction...")
                tx.sign(treasury)
                serialized_tx = tx.serialize()
                
                result = client.send_raw_transaction(serialized_tx)
                signature = result.value  # Changed from result['result']
                
                print("Waiting for confirmation...")
                confirmation = client.confirm_transaction(signature)  # Use signature directly
                if confirmation.value:  # Changed from confirmation
                    print(f"Transaction confirmed! Signature: {signature}")
                    print(f"Successfully funded {swarm_id} hot wallet")
                    time.sleep(2)
                    break
                else:
                    raise Exception("Transaction not confirmed")
                
            except Exception as e:
                print(f"Error funding {swarm_id} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    print("Full error traceback:")
                    import traceback
                    print(traceback.format_exc())

def main():
    print("Starting hot wallet funding process...")
    fund_hot_wallets()
    print("\nFunding process complete!")

if __name__ == "__main__":
    main()
