import os
import json
import glob
import codecs
import sys
from solders.keypair import Keypair
from solana.rpc.api import Client
from solana.transaction import Transaction
from solders.system_program import transfer, TransferParams
from spl.token.instructions import transfer as spl_transfer
from dotenv import load_dotenv

# Force UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

load_dotenv()

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
    """Fund hot wallets with initial SOL and COMPUTE"""
    client = Client(os.getenv('SOLANA_RPC_URL'))
    
    # Load funding wallet (treasury)
    treasury_keypair = Keypair.from_bytes(bytes.fromhex(os.getenv('TREASURY_PRIVATE_KEY')))
    compute_token_mint = os.getenv('COMPUTE_TOKEN_ADDRESS')
    
    swarms = load_swarms_with_hot_wallets()
    print(f"\nFound {len(swarms)} hot wallets to fund")
    
    for swarm_id, swarm in swarms.items():
        hot_wallet = swarm['hotWallet']
        print(f"\nProcessing {swarm_id}")
        print(f"Hot wallet: {hot_wallet}")
        
        try:
            # Create SOL transfer transaction (0.01 SOL)
            sol_tx = Transaction()
            sol_tx.add(transfer(
                TransferParams(
                    from_pubkey=treasury_keypair.pubkey(),
                    to_pubkey=hot_wallet,
                    lamports=10000000  # 0.01 SOL in lamports
                )
            ))
            
            # Send SOL transaction
            print("Sending 0.01 SOL...")
            sol_result = client.send_transaction(sol_tx, treasury_keypair)
            print(f"SOL transfer signature: {sol_result['result']}")
            
            # Create COMPUTE transfer transaction (1M tokens)
            compute_tx = Transaction()
            compute_tx.add(spl_transfer(
                treasury_keypair.pubkey(),
                hot_wallet,
                1000000,  # 1M COMPUTE
                compute_token_mint
            ))
            
            # Send COMPUTE transaction
            print("Sending 1M COMPUTE...")
            compute_result = client.send_transaction(compute_tx, treasury_keypair)
            print(f"COMPUTE transfer signature: {compute_result['result']}")
            
            print(f"Successfully funded {swarm_id} hot wallet")
            
        except Exception as e:
            print(f"Error funding {swarm_id}: {str(e)}")

def main():
    print("Starting hot wallet funding process...")
    fund_hot_wallets()
    print("\nFunding process complete!")

if __name__ == "__main__":
    main()
