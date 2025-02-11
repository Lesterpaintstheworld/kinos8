import glob
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from pathlib import Path

def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_swarms():
    swarms = {}
    swarms_dir = Path('data/swarms')
    for file_path in swarms_dir.glob('*.json'):
        swarm = load_json_file(file_path)
        swarms[swarm['swarmId']] = swarm
    return swarms

def load_active_collaborations():
    collabs = []
    collabs_dir = Path('data/collaborations')
    for file_path in collabs_dir.glob('*.json'):
        collab = load_json_file(file_path)
        if collab.get('status') == 'active':
            collabs.append(collab)
    return collabs

def calculate_distributions():
    swarms = load_swarms()
    active_collabs = load_active_collaborations()
    
    # Group collaborations by provider
    provider_totals = {}
    
    for collab in active_collabs:
        provider_id = collab['providerSwarmId']
        if provider_id not in provider_totals:
            provider_totals[provider_id] = {
                'total': 0,
                'collaborations': []
            }
        provider_totals[provider_id]['total'] += collab['price']
        provider_totals[provider_id]['collaborations'].append(collab)

    results = {}
    
    for provider_id, data in provider_totals.items():
        total = data['total']
        provider_swarm = swarms[provider_id]
        revenue_share = provider_swarm.get('revenueShare', 10)  # Default to 10% if not specified
        
        # Calculate burns (50% of total)
        burn_amount = total * 0.5
        burn_compute = burn_amount * 0.9  # 90% of burn in COMPUTE
        burn_ubc = burn_amount * 0.1     # 10% of burn in UBC
        
        # Calculate redistribution (revenueShare% of total)
        redistribution_amount = total * (revenue_share / 100)
        redistribution_compute = redistribution_amount * 0.9  # 90% in COMPUTE
        redistribution_ubc = redistribution_amount * 0.1     # 10% in UBC
        
        # Calculate net (remaining after burns and redistributions)
        net_amount = total - burn_amount - redistribution_amount
        
        results[provider_id] = {
            'total': total,
            'burn': {
                'total': burn_amount,
                'compute': burn_compute,
                'ubc': burn_ubc
            },
            'redistribution': {
                'total': redistribution_amount,
                'compute': redistribution_compute,
                'ubc': redistribution_ubc,
                'share': revenue_share
            },
            'net': net_amount,
            'collaborations': [
                {
                    'id': c['collaborationId'],
                    'client': c['clientSwarmId'],
                    'price': c['price']
                } for c in data['collaborations']
            ]
        }
    
    return results

def calculate_grand_totals(results):
    totals = {
        'revenue': 0,
        'burn_compute': 0,
        'burn_ubc': 0,
        'redistribution_compute': 0,
        'redistribution_ubc': 0,
        'net': 0
    }
    
    for data in results.values():
        totals['revenue'] += data['total']
        totals['burn_compute'] += data['burn']['compute']
        totals['burn_ubc'] += data['burn']['ubc']
        totals['redistribution_compute'] += data['redistribution']['compute']
        totals['redistribution_ubc'] += data['redistribution']['ubc']
        totals['net'] += data['net']
    
    return totals

def update_swarm_revenues(results):
    """Update swarm weekly revenues based on distribution results and push to Airtable"""
    print("\nUpdating swarm revenues...")
    
    try:
        # Load all swarms first
        swarms = {}
        swarm_files = glob.glob('data/swarms/*.json')
        for file in swarm_files:
            with open(file, 'r', encoding='utf-8') as f:
                swarm_data = json.load(f)
                swarms[swarm_data['swarmId']] = swarm_data
        
        # Update revenues based on distribution results
        for swarm_id, data in results.items():
            if swarm_id in swarms:
                # Update weekly revenue with net amount
                swarms[swarm_id]['weeklyRevenue'] = int(data['net'])
                swarms[swarm_id]['totalRevenue'] = swarms[swarm_id].get('totalRevenue', 0) + int(data['net'])
                
                # Save updated swarm data
                with open(f'data/swarms/{swarm_id}.json', 'w', encoding='utf-8') as f:
                    json.dump(swarms[swarm_id], f, indent=2, ensure_ascii=False)
                print(f"Updated {swarm_id} weekly revenue to {data['net']:,} $COMPUTE")
        
        # Push only swarms to Airtable
        print("\nPushing swarm updates to Airtable...")
        subprocess.run(["python", "scripts/pushData.py", "--table", "Swarms"], check=True)
        print("Swarm updates pushed to Airtable successfully")
        
    except Exception as e:
        print(f"Error updating swarm revenues: {str(e)}")

def format_results(results):
    output = []
    for provider_id, data in results.items():
        output.append(f"\n{provider_id.upper()} Weekly Distributions:")
        output.append(f"Total Revenue: {data['total']:,} $COMPUTE")
        
        output.append("\nCollaborations:")
        for collab in data['collaborations']:
            output.append(f"- {collab['client']}: {collab['price']:,} $COMPUTE")
        
        output.append(f"\nBurns (50%):")
        output.append(f"- {data['burn']['compute']:,.0f} $COMPUTE")
        output.append(f"- {data['burn']['ubc']:,.0f} UBC")
        
        output.append(f"\nRedistributions ({data['redistribution']['share']}%):")
        output.append(f"- {data['redistribution']['compute']:,.0f} $COMPUTE")
        output.append(f"- {data['redistribution']['ubc']:,.0f} UBC")
        
        output.append(f"\nNet Revenue: {data['net']:,.0f} $COMPUTE")
        output.append("-" * 50)
    
    # Add grand totals
    totals = calculate_grand_totals(results)
    output.append("\nGRAND TOTALS")
    output.append(f"Total Weekly Revenue: {totals['revenue']:,} $COMPUTE")
    output.append("\nTotal Burns:")
    output.append(f"- {totals['burn_compute']:,.0f} $COMPUTE")
    output.append(f"- {totals['burn_ubc']:,.0f} UBC")
    output.append("\nTotal Redistributions:")
    output.append(f"- {totals['redistribution_compute']:,.0f} $COMPUTE")
    output.append(f"- {totals['redistribution_ubc']:,.0f} UBC")
    output.append(f"\nTotal Net Revenue: {totals['net']:,.0f} $COMPUTE")
    output.append("-" * 50)
    
    return "\n".join(output)

def main():
    # Create reports directory if it doesn't exist
    Path('data/reports').mkdir(parents=True, exist_ok=True)
    
    results = calculate_distributions()
    print(format_results(results))
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f'data/reports/distributions_{timestamp}.txt', 'w') as f:
        f.write(format_results(results))
    
    # Update swarm revenues and push to Airtable
    update_swarm_revenues(results)

if __name__ == "__main__":
    main()
