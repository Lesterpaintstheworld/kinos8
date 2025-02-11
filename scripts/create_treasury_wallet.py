import os
import json
from solders.keypair import Keypair
import base58
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

load_dotenv()

class TreasuryManager:
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

    def create_treasury_wallet(self):
        """Create and store encrypted treasury wallet"""
        print("\nCreating treasury wallet...")
        try:
            # Generate new keypair
            print("Generating keypair...")
            keypair = Keypair()
            
            # Get keys
            public_key = str(keypair.pubkey())
            private_key = base58.b58encode(bytes(keypair)).decode('ascii')
            print(f"Generated public key: {public_key}")
            
            # Encrypt private key
            print("Encrypting private key...")
            encrypted_key = self.fernet.encrypt(private_key.encode()).decode()
            
            # Save encrypted key
            print("Saving encrypted key...")
            os.makedirs('secure', exist_ok=True)
            with open('secure/treasury_wallet.enc', 'w') as f:
                f.write(encrypted_key)
            print("Encrypted key saved to secure/treasury_wallet.enc")
            
            # Save public key to .env
            env_path = '.env'
            env_lines = []
            treasury_line = f'TREASURY_WALLET={public_key}'
            
            # Read existing .env content
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    env_lines = f.readlines()
            
            # Update or add TREASURY_WALLET
            treasury_found = False
            for i, line in enumerate(env_lines):
                if line.startswith('TREASURY_WALLET='):
                    env_lines[i] = treasury_line + '\n'
                    treasury_found = True
                    break
            
            if not treasury_found:
                env_lines.append(treasury_line + '\n')
            
            # Write back to .env
            with open(env_path, 'w') as f:
                f.writelines(env_lines)
            
            print(f"\nTreasury wallet creation complete")
            print(f"Public Key: {public_key}")
            print(f"Added to .env as TREASURY_WALLET")
            return public_key
            
        except Exception as e:
            print(f"Error creating treasury wallet: {str(e)}")
            raise

def main():
    treasury_manager = TreasuryManager()
    treasury_manager.create_treasury_wallet()

if __name__ == "__main__":
    main()
