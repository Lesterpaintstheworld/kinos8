import json
import glob
import os
from collections import defaultdict
from pathlib import Path

def load_json_file(file_path):
    try:
        with Path(file_path).open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {file_path}: {str(e)}")
        return None

def get_swarm_services():
    # Map swarmId -> list of serviceIds
    swarm_services = defaultdict(list)
    service_files = glob.glob('data/services/*.json')
    
    for file_path in service_files:
        data = load_json_file(file_path)
        if data and 'serviceId' in data and 'swarmId' in data:
            swarm_services[data['swarmId']].append(data['serviceId'])
    
    return swarm_services

def analyze_swarm_relations():
    # Debug prints
    print("\nDEBUG INFO:")
    
    # Check collaborations structure
    collab_files = glob.glob('data/collaborations/*.json')
    print(f"Found {len(collab_files)} collaboration files")
    for collab_file in collab_files[:2]:  # Print first 2 as sample
        data = load_json_file(collab_file)
        print(f"Sample collaboration file {collab_file}:")
        print(data)
    
    # Check messages structure
    message_files = glob.glob('data/messages/*.json')
    print(f"\nFound {len(message_files)} message files")
    for msg_file in message_files[:2]:  # Print first 2 as sample
        data = load_json_file(msg_file)
        print(f"Sample message file {msg_file}:")
        print(data)

    # Get all swarms first
    swarm_files = list(Path('data/swarms').glob('*.json'))
    swarm_relations = defaultdict(lambda: defaultdict(list))
    
    # Get service mappings
    swarm_services = get_swarm_services()
    
    # Process each swarm
    for swarm_file in swarm_files:
        swarm_data = load_json_file(str(swarm_file))
        if not swarm_data or 'swarmId' not in swarm_data:
            continue
        
        swarm_id = swarm_data['swarmId']
        swarm_relations[swarm_id]['swarm_files'].append(f"swarms/{swarm_file.name}")
        
        # Add services
        if swarm_id in swarm_services:
            for service_id in swarm_services[swarm_id]:
                swarm_relations[swarm_id]['services'].append(f"services/{service_id}.json")
                
        # Check missions where swarm is lead or assigned
        mission_files = list(Path('data/missions').glob('*.json'))
        for mission_file in mission_files:
            data = load_json_file(mission_file)
            if data:
                # Check if swarm is either lead or assigned
                is_lead = data.get('leadSwarm') == swarm_id
                is_assigned = isinstance(data.get('assignedSwarms'), list) and swarm_id in data['assignedSwarms']
                
                if is_lead or is_assigned:
                    mission_id = data.get('missionId')
                    if mission_id:
                        relation_type = 'lead_missions' if is_lead else 'assigned_missions'
                        swarm_relations[swarm_id][relation_type].append(f"missions/{mission_id}.json")
        
        # Check collaborations
        collab_files = list(Path('data/collaborations').glob('*.json'))
        for collab_file in collab_files:
            data = load_json_file(collab_file)
            if data:
                # Check if swarm is either client or provider
                if (data.get('clientSwarmId') == swarm_id or 
                    data.get('providerSwarmId') == swarm_id):
                    collab_id = data.get('collaborationId')
                    if collab_id:
                        swarm_relations[swarm_id]['collaborations'].append(f"collaborations/{collab_id}.json")
                        
                        # Check specifications linked to this collaboration
                        spec_files = list(Path('data/specifications').glob('*.json'))
                        for spec_file in spec_files:
                            spec_data = load_json_file(spec_file)
                            if spec_data and 'collaborationId' in spec_data and spec_data['collaborationId'] == collab_id:
                                swarm_relations[swarm_id]['specifications'].append(f"specifications/{spec_data['specificationId']}.json")
                
                        # Check messages linked to this collaboration
                        message_files = list(Path('data/messages').glob('*.json'))
                        for msg_file in message_files:
                            msg_data = load_json_file(msg_file)
                            if msg_data and 'collaborationId' in msg_data and msg_data['collaborationId'] == collab_id:
                                swarm_relations[swarm_id]['messages'].append(f"messages/{msg_data['messageId']}.json")
        
        # Check messages
        message_files = list(Path('data/messages').glob('*.json'))
        for msg_file in message_files:
            data = load_json_file(msg_file)
            if data and 'senderId' in data and data['senderId'] == swarm_id:
                swarm_relations[swarm_id]['messages'].append(f"messages/{data['messageId']}.json")
        
        # Check news
        news_files = list(Path('data/news').glob('*.json'))
        for news_file in news_files:
            data = load_json_file(news_file)
            if data and 'swarmId' in data and data['swarmId'] == swarm_id:
                swarm_relations[swarm_id]['news'].append(f"news/{data['newsId']}.json")
    
    return swarm_relations

def main():
    relations = analyze_swarm_relations()
    
    # Print results in a simplified way
    for swarm_id, related_items in relations.items():
        print(f"\n{swarm_id}")
        for category, items in related_items.items():
            if items:  # Only print categories that have items
                print(f"\n{category.replace('_', ' ').title()}:")
                for item in items:
                    print(f"  data/{item}")
        print()

if __name__ == '__main__':
    main()
