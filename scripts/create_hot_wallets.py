import os
import json
import glob
from solders.keypair import Keypair
import base58
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv
import subprocess

load_dotenv()

class WalletManager:
    def __init__(self):
        self.master_key = self._derive_master_key()
        self.fernet = Fernet(self.master_key)
        
    def _derive_master_key(self):
        """Create encryption key from environment variables"""
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
        return base64.urlsafe_b64encode(kdf.derive(password))

    def create_hot_wallet(self, swarm_id):
        """Create and store encrypted hot wallet"""
        print(f"\nCreating hot wallet for {swarm_id}...")
        try:
            # Generate new keypair
            print("Generating keypair...")
            keypair = Keypair()
            
            # Get keys
            public_key = str(keypair.public_key)
            private_key = base58.b58encode(keypair.seed).decode('ascii')
            print(f"Generated public key: {public_key}")
            
            # Encrypt private key
            print("Encrypting private key...")
            encrypted_key = self.fernet.encrypt(private_key.encode()).decode()
            
            # Save encrypted key
            print("Saving encrypted key...")
            os.makedirs('secure', exist_ok=True)
            with open(f'secure/{swarm_id}_wallet.enc', 'w') as f:
                f.write(encrypted_key)
            print(f"Encrypted key saved to secure/{swarm_id}_wallet.enc")
                
            # Update swarm file with public key
            print(f"Updating swarm data for {swarm_id}...")
            swarm_file = f'data/swarms/{swarm_id}.json'
            with open(swarm_file, 'r') as f:
                swarm_data = json.load(f)
            
            swarm_data['hotWallet'] = public_key
            
            with open(swarm_file, 'w') as f:
                json.dump(swarm_data, f, indent=2)
            print(f"Updated swarm file with hot wallet public key")
                
            # Push update to Airtable
            print("\nPushing update to Airtable...")
            subprocess.run(["python", "scripts/pushData.py", "--table", "Swarms"], check=True)
            print("Airtable update complete")
            
            print(f"\nHot wallet creation complete for {swarm_id}")
            print(f"Public Key: {public_key}")
            return public_key
            
        except Exception as e:
            print(f"Error creating hot wallet for {swarm_id}: {str(e)}")
            raise

def main():
    wallet_manager = WalletManager()
    
    # Process all swarms without hot wallets
    swarm_files = glob.glob('data/swarms/*.json')
    for file in swarm_files:
        with open(file) as f:
            swarm = json.load(f)
            if 'hotWallet' not in swarm:
                print(f"\nProcessing {swarm['swarmId']}...")
                wallet_manager.create_hot_wallet(swarm['swarmId'])

if __name__ == "__main__":
    main()
