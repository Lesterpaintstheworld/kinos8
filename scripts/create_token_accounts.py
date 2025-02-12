import os
import json
import glob
import codecs
import sys
import base64
import base58
import time
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from solders.keypair import Keypair
from solana.rpc.api import Client
from solana.transaction import Transaction
from solders.pubkey import Pubkey
from spl.token.instructions import create_associated_token_account, get_associated_token_address
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from dotenv import load_dotenv

# Force UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

load_dotenv()

# Token addresses
COMPUTE_TOKEN = "B1N1HcMm4RysYz4smsXwmk2UnS8NziqKCM6Ho8i62vXo"
UBC_TOKEN = "9psiRdn9cXYVps4F1kFuoNjd2EtmqNJXrCPmRppJpump"

def load_treasury_wallet():
    """Load encrypted treasury wallet"""
    try:
        with open('secure/treasury_wallet.enc', 'r') as f:
            encrypted_key = f.read()
            
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

def create_token_accounts():
    """Create token accounts for all hot wallets"""
    # Load treasury wallet as payer
    treasury = load_treasury_wallet()
    if not treasury:
        print("Failed to load treasury wallet")
        return
        
    print(f"Loaded treasury wallet: {treasury.pubkey()}")
    
    # Load all swarms with hot wallets
    swarms = load_swarms_with_hot_wallets()
    print(f"\nFound {len(swarms)} hot wallets to process")
    
    # Initialize Solana client
    helius_url = os.getenv('NEXT_PUBLIC_HELIUS_RPC_URL')
    if not helius_url:
        print("Error: NEXT_PUBLIC_HELIUS_RPC_URL not found in environment variables")
        return
        
    client = Client(helius_url)
    print(f"Connected to Helius RPC endpoint")
    
    # Process each hot wallet
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
                
                # Create token accounts
                for token_mint in [COMPUTE_TOKEN, UBC_TOKEN]:
                    token_name = "COMPUTE" if token_mint == COMPUTE_TOKEN else "UBC"
                    print(f"\nCreating {token_name} token account...")
                    
                    # Convert addresses to Pubkeys
                    hot_wallet_pubkey = Pubkey.from_string(hot_wallet)
                    mint_pubkey = Pubkey.from_string(token_mint)
                    
                    # Get the associated token account address
                    ata = get_associated_token_address(
                        owner=hot_wallet_pubkey,
                        mint=mint_pubkey
                    )
                    
                    # Create instruction to create the associated token account
                    create_ata_ix = create_associated_token_account(
                        payer=treasury.pubkey(),
                        owner=hot_wallet_pubkey,
                        mint=mint_pubkey
                    )
                    
                    # Create transaction
                    tx = Transaction()
                    tx.add(create_ata_ix)
                    tx.recent_blockhash = recent_blockhash
                    
                    # Sign and send transaction
                    print(f"Sending create {token_name} account transaction...")
                    tx.sign(treasury)
                    result = client.send_raw_transaction(tx.serialize())
                    signature = result.value
                    
                    print("Waiting for confirmation...")
                    confirmation = client.confirm_transaction(signature)
                    if confirmation.value:
                        print(f"{token_name} token account created successfully!")
                    else:
                        raise Exception(f"{token_name} account creation not confirmed")
                    
                    # Add delay between transactions
                    time.sleep(2)
                
                print(f"\nSuccessfully created token accounts for {swarm_id}")
                break
                
            except Exception as e:
                print(f"Error processing {swarm_id} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    print("Full error traceback:")
                    import traceback
                    print(traceback.format_exc())

def main():
    print("Starting token account creation process...")
    create_token_accounts()
    print("\nToken account creation process complete!")

if __name__ == "__main__":
    main()
