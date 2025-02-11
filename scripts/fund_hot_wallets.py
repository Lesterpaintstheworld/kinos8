import os
import json
import glob
import codecs
import sys
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
    """Generate Phantom URLs to fund hot wallets with initial SOL and COMPUTE"""
    treasury_wallet = os.getenv('TREASURY_WALLET')  # Public key only
    compute_token_mint = os.getenv('COMPUTE_TOKEN_ADDRESS')
    
    swarms = load_swarms_with_hot_wallets()
    print(f"\nFound {len(swarms)} hot wallets to fund")
    
    # Create URLs for each wallet
    try:
        for batch_num, (swarm_id, swarm) in enumerate(swarms.items(), 1):
            hot_wallet = swarm['hotWallet']
            print(f"\nGenerating funding URLs for {swarm_id}")
            print(f"Hot wallet: {hot_wallet}")
            
            # Generate SOL transfer URL
            sol_url = (f"https://phantom.app/ul/v1/transfer?"
                      f"from={treasury_wallet}&"
                      f"to={hot_wallet}&"
                      f"amount=10000000&"  # 0.01 SOL
                      f"memo=Initial+SOL+funding+for+{swarm_id}")
            
            # Generate COMPUTE transfer URL
            compute_url = (f"https://phantom.app/ul/v1/transfer?"
                         f"from={treasury_wallet}&"
                         f"to={hot_wallet}&"
                         f"amount=1000000&"  # 1M COMPUTE
                         f"splToken={compute_token_mint}&"
                         f"memo=Initial+COMPUTE+funding+for+{swarm_id}")
            
            print("\nSOL funding URL:")
            print(sol_url)
            print("\nCOMPUTE funding URL:")
            print(compute_url)
            
            if batch_num < len(swarms):
                print("\nProcess these URLs, then press Enter for next wallet...")
                input()
        
        print("\nAll funding URLs generated!")
        
    except Exception as e:
        print(f"Error generating URLs: {str(e)}")

def main():
    print("Starting hot wallet funding process...")
    fund_hot_wallets()
    print("\nFunding process complete!")

if __name__ == "__main__":
    main()
