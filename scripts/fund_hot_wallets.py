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
    
    # Create batched URLs
    try:
        # Split into batches of 5 wallets
        BATCH_SIZE = 5
        all_hot_wallets = [(swarm_id, swarm['hotWallet']) for swarm_id, swarm in swarms.items()]
        batches = [all_hot_wallets[i:i + BATCH_SIZE] for i in range(0, len(all_hot_wallets), BATCH_SIZE)]
        
        print(f"\nSplit into {len(batches)} batches of {BATCH_SIZE} wallets each")
        
        for batch_num, wallet_batch in enumerate(batches, 1):
            print(f"\nBatch {batch_num}/{len(batches)}:")
            
            # Generate SOL transfer URL for this batch
            transfers_str = ','.join([f'{wallet}:10000000' for _, wallet in wallet_batch])
            sol_url = (f"https://phantom.app/ul/v1/batch-transfer?"
                      f"from={treasury_wallet}&"
                      f"transfers={transfers_str}&"
                      f"memo=Initial+SOL+funding+batch+{batch_num}")
            
            # Generate COMPUTE transfer URL for this batch
            compute_url = (f"https://phantom.app/ul/v1/batch-transfer?"
                         f"from={treasury_wallet}&"
                         f"transfers={transfers_str}&"
                         f"splToken={compute_token_mint}&"
                         f"memo=Initial+COMPUTE+funding+batch+{batch_num}")
            
            print("\nSOL funding URL:")
            print(sol_url)
            print("\nCOMPUTE funding URL:")
            print(compute_url)
            
            if batch_num < len(batches):
                print("\nProcess these URLs, then press Enter for next batch...")
                input()
        
        print("\nAll funding URLs generated!")
        
    except Exception as e:
        print(f"Error generating batch URLs: {str(e)}")

def main():
    print("Starting hot wallet funding process...")
    fund_hot_wallets()
    print("\nFunding process complete!")

if __name__ == "__main__":
    main()
