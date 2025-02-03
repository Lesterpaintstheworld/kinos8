import json
import glob
import os
from collections import defaultdict

def load_json_file(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except:
        print(f"Warning: Could not load {file_path}")
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
    swarm_files = glob.glob('data/swarms/*.json')
    swarm_relations = defaultdict(lambda: defaultdict(list))
    
    # Get service mappings
    swarm_services = get_swarm_services()
    
    # Process each swarm
    for swarm_file in swarm_files:
        swarm_data = load_json_file(swarm_file)
        if not swarm_data or 'swarmId' not in swarm_data:
            continue
        
        swarm_id = swarm_data['swarmId']
        swarm_relations[swarm_id]['swarm_files'].append(os.path.basename(swarm_file))
        
        # Add services
        if swarm_id in swarm_services:
            for service_id in swarm_services[swarm_id]:
                swarm_relations[swarm_id]['services'].append(f"services/{service_id}.json")
        
        # Check collaborations
        collab_files = glob.glob('data/collaborations/*.json')
        for collab_file in collab_files:
            data = load_json_file(collab_file)
            if data and 'swarmId' in data and data['swarmId'] == swarm_id:
                collab_id = data.get('collaborationId')
                if collab_id:
                    swarm_relations[swarm_id]['collaborations'].append(f"collaborations/{collab_id}.json")
                    
                    # Check specifications linked to this collaboration
                    spec_files = glob.glob('data/specifications/*.json')
                    for spec_file in spec_files:
                        spec_data = load_json_file(spec_file)
                        if spec_data and 'collaborationId' in spec_data and spec_data['collaborationId'] == collab_id:
                            swarm_relations[swarm_id]['specifications'].append(f"specifications/{spec_data['specificationId']}.json")
            
                    # Check messages linked to this collaboration
                    message_files = glob.glob('data/messages/*.json')
                    for msg_file in message_files:
                        msg_data = load_json_file(msg_file)
                        if msg_data and 'collaborationId' in msg_data and msg_data['collaborationId'] == collab_id:
                            swarm_relations[swarm_id]['messages'].append(f"messages/{msg_data['messageId']}.json")
        
        # Check messages
        message_files = glob.glob('data/messages/*.json')
        for msg_file in message_files:
            data = load_json_file(msg_file)
            if data and 'swarmId' in data and data['swarmId'] == swarm_id:
                swarm_relations[swarm_id]['messages'].append(f"messages/{data['messageId']}.json")
        
        # Check news
        news_files = glob.glob('data/news/*.json')
        for news_file in news_files:
            data = load_json_file(news_file)
            if data and 'swarmId' in data and data['swarmId'] == swarm_id:
                swarm_relations[swarm_id]['news'].append(f"news/{data['newsId']}.json")
    
    return swarm_relations

def main():
    relations = analyze_swarm_relations()
    
    # Print results in a structured way
    for swarm_id, related_items in relations.items():
        print(f"\n=== Swarm: {swarm_id} ===")
        
        for category, items in related_items.items():
            if items:
                print(f"\n{category.upper()}:")
                for item in items:
                    print(f"  - {item}")
        
        print("\n" + "="*50)

if __name__ == '__main__':
    main()
