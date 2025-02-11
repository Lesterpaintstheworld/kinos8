import os
import json
import glob
from solana.keypair import Keypair
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
        # Generate new keypair
        keypair = Keypair()
        
        # Get keys
        public_key = str(keypair.public_key)
        private_key = base58.b58encode(keypair.seed).decode('ascii')
        
        # Encrypt private key
        encrypted_key = self.fernet.encrypt(private_key.encode()).decode()
        
        # Save encrypted key
        os.makedirs('secure', exist_ok=True)
        with open(f'secure/{swarm_id}_wallet.enc', 'w') as f:
            f.write(encrypted_key)
            
        # Update swarm file with public key
        swarm_file = f'data/swarms/{swarm_id}.json'
        with open(swarm_file, 'r') as f:
            swarm_data = json.load(f)
        
        swarm_data['hotWallet'] = public_key
        
        with open(swarm_file, 'w') as f:
            json.dump(swarm_data, f, indent=2)
            
        # Push update to Airtable
        subprocess.run(["python", "scripts/pushData.py", "--table", "Swarms"], check=True)
        
        print(f"Created hot wallet for {swarm_id}")
        print(f"Public Key: {public_key}")
        return public_key

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
