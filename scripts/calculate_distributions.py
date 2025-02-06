import json
import os
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

if __name__ == "__main__":
    main()
