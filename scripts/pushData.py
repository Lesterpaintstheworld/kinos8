import os
from dotenv import load_dotenv
from pyairtable import Api
import json
import glob

def get_table_schema(table):
    """Get the available fields for a table by checking a sample record"""
    try:
        sample = table.all(max_records=1)
        if sample:
            # Get fields from first record
            return set(sample[0]['fields'].keys())
        return set()
    except Exception as e:
        print(f"Warning: Could not get schema - {str(e)}")
        return set()

def filter_data_for_table(data, valid_fields):
    """Remove any fields that don't exist in the Airtable schema"""
    return {k: v for k, v in data.items() if k in valid_fields}

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
if not AIRTABLE_API_KEY:
    raise ValueError("AIRTABLE_API_KEY environment variable is required")

# Get base ID from environment variable
BASE_ID = os.getenv('AIRTABLE_BASE_ID')
if not BASE_ID:
    raise ValueError("AIRTABLE_BASE_ID environment variable is required")

# Initialize Airtable API
api = Api(AIRTABLE_API_KEY)

def push_swarms():
    print("\nProcessing Swarms...")
    table = api.table(BASE_ID, 'Swarms')
    swarm_files = glob.glob('data/swarms/*.json')
    print(f"Found {len(swarm_files)} swarm files to process")
    
    existing_records = table.all()
    existing_ids = {record['fields'].get('swarmId'): record['id'] 
                   for record in existing_records 
                   if 'swarmId' in record['fields']}
    
    updated_count = created_count = skipped_count = 0
    
    for file_path in swarm_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            swarm_id = data.get('swarmId')
            if not swarm_id:
                print(f"Warning: Skipping file {file_path} - missing swarmId")
                skipped_count += 1
                continue
            
            if swarm_id in existing_ids:
                table.update(existing_ids[swarm_id], data)
                print(f"Updated swarm: {swarm_id}")
                updated_count += 1
            else:
                table.create(data)
                print(f"Created new swarm: {swarm_id}")
                created_count += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            skipped_count += 1
    
    print(f"\nCompleted Swarms:")
    print(f"  - Created: {created_count}")
    print(f"  - Updated: {updated_count}")
    if skipped_count > 0:
        print(f"  - Skipped: {skipped_count}")

def push_services():
    print("\nProcessing Services...")
    table = api.table(BASE_ID, 'Services')
    service_files = glob.glob('data/services/*.json')
    print(f"Found {len(service_files)} service files to process")
    
    existing_records = table.all()
    existing_ids = {record['fields'].get('serviceId'): record['id'] 
                   for record in existing_records 
                   if 'serviceId' in record['fields']}
    
    updated_count = created_count = skipped_count = 0
    
    for file_path in service_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            service_id = data.get('serviceId')
            if not service_id:
                print(f"Warning: Skipping file {file_path} - missing serviceId")
                skipped_count += 1
                continue
            
            if service_id in existing_ids:
                table.update(existing_ids[service_id], data)
                print(f"Updated service: {service_id}")
                updated_count += 1
            else:
                table.create(data)
                print(f"Created new service: {service_id}")
                created_count += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            skipped_count += 1
    
    print(f"\nCompleted Services:")
    print(f"  - Created: {created_count}")
    print(f"  - Updated: {updated_count}")
    if skipped_count > 0:
        print(f"  - Skipped: {skipped_count}")

def push_messages():
    print("\nProcessing Messages...")
    table = api.table(BASE_ID, 'Messages')
    
    # Define standard message fields excluding timestamp
    standard_fields = {
        'messageId',
        'senderId', 
        'receiverId',
        'collaborationId',
        'content'
    }
    
    message_files = glob.glob('data/messages/*.json')
    print(f"Found {len(message_files)} message files to process")
    
    existing_records = table.all()
    existing_ids = {record['fields'].get('messageId'): record['id'] 
                   for record in existing_records 
                   if 'messageId' in record['fields']}
    
    updated_count = created_count = skipped_count = 0
    
    for file_path in message_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Filter out non-standard fields
            filtered_data = {k: v for k, v in data.items() if k in standard_fields}
            
            message_id = data.get('messageId')
            if not message_id:
                print(f"Warning: Skipping file {file_path} - missing messageId")
                skipped_count += 1
                continue
            
            if message_id in existing_ids:
                table.update(existing_ids[message_id], data)
                print(f"Updated message: {message_id}")
                updated_count += 1
            else:
                table.create(data)
                print(f"Created new message: {message_id}")
                created_count += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            skipped_count += 1
    
    print(f"\nCompleted Messages:")
    print(f"  - Created: {created_count}")
    print(f"  - Updated: {updated_count}")
    if skipped_count > 0:
        print(f"  - Skipped: {skipped_count}")

def push_news():
    print("\nProcessing News...")
    table = api.table(BASE_ID, 'News')
    news_files = glob.glob('data/news/*.json')
    print(f"Found {len(news_files)} news files to process")
    
    existing_records = table.all()
    existing_ids = {record['fields'].get('newsId'): record['id'] 
                   for record in existing_records 
                   if 'newsId' in record['fields']}
    
    updated_count = created_count = skipped_count = 0
    
    for file_path in news_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            news_id = data.get('newsId')
            if not news_id:
                print(f"Warning: Skipping file {file_path} - missing newsId")
                skipped_count += 1
                continue
            
            if news_id in existing_ids:
                table.update(existing_ids[news_id], data)
                print(f"Updated news: {news_id}")
                updated_count += 1
            else:
                table.create(data)
                print(f"Created new news: {news_id}")
                created_count += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            skipped_count += 1
    
    print(f"\nCompleted News:")
    print(f"  - Created: {created_count}")
    print(f"  - Updated: {updated_count}")
    if skipped_count > 0:
        print(f"  - Skipped: {skipped_count}")

def push_collaborations():
    print("\nProcessing Collaborations...")
    
    # Get the table
    table = api.table(BASE_ID, 'Collaborations')
    
    # Get valid fields for this table
    valid_fields = get_table_schema(table)
    print(f"Valid fields for Collaborations: {valid_fields}")
    
    # Get all collaboration files
    collab_files = glob.glob('data/collaborations/*.json')
    print(f"Found {len(collab_files)} collaboration files to process")
    
    # Get existing records to update instead of create if they exist
    existing_records = table.all()
    existing_ids = {record['fields'].get('collaborationId'): record['id'] 
                   for record in existing_records 
                   if 'collaborationId' in record['fields']}
    
    updated_count = 0
    created_count = 0
    skipped_count = 0
    
    for file_path in collab_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Filter data to only include valid fields
            filtered_data = filter_data_for_table(data, valid_fields)
            
            collab_id = data.get('collaborationId')
            if not collab_id:
                print(f"Warning: Skipping file {file_path} - missing collaborationId")
                skipped_count += 1
                continue
            
            # If record exists, update it
            if collab_id in existing_ids:
                table.update(existing_ids[collab_id], filtered_data)
                print(f"Updated collaboration: {collab_id}")
                updated_count += 1
            # If record is new, create it
            else:
                table.create(filtered_data)
                print(f"Created new collaboration: {collab_id}")
                created_count += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            skipped_count += 1
    
    print(f"\nCompleted Collaborations:")
    print(f"  - Created: {created_count}")
    print(f"  - Updated: {updated_count}")
    if skipped_count > 0:
        print(f"  - Skipped: {skipped_count}")

def push_specifications():
    print("\nProcessing Specifications...")
    
    table = api.table(BASE_ID, 'Specifications')
    
    # Define the standard fields we know Airtable accepts
    standard_fields = {
        'specificationId',
        'collaborationId',
        'title',
        'createdAt',
        'content'
    }
    
    spec_files = glob.glob('data/specifications/*.json')
    print(f"Found {len(spec_files)} specification files to process")
    
    existing_records = table.all()
    existing_ids = {record['fields'].get('specificationId'): record['id'] 
                   for record in existing_records 
                   if 'specificationId' in record['fields']}
    
    updated_count = created_count = skipped_count = 0
    
    for file_path in spec_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Filter out non-standard fields
            filtered_data = {k: v for k, v in data.items() if k in standard_fields}
            
            spec_id = filtered_data.get('specificationId')
            if not spec_id:
                print(f"Warning: Skipping file {file_path} - missing specificationId")
                skipped_count += 1
                continue
            
            if spec_id in existing_ids:
                table.update(existing_ids[spec_id], filtered_data)
                print(f"Updated specification: {spec_id}")
                updated_count += 1
            else:
                table.create(filtered_data)
                print(f"Created new specification: {spec_id}")
                created_count += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            skipped_count += 1
    
    print(f"\nCompleted Specifications:")
    print(f"  - Created: {created_count}")
    print(f"  - Updated: {updated_count}")
    if skipped_count > 0:
        print(f"  - Skipped: {skipped_count}")

def push_deliverables():
    print("\nProcessing Deliverables...")
    
    table = api.table(BASE_ID, 'Deliverables')
    
    # Define the standard fields we know Airtable accepts
    # Removed 'status' since it's not accepted
    standard_fields = {
        'deliverableId',
        'collaborationId',
        'title',
        'content',
        'createdAt'
    }
    
    deliv_files = glob.glob('data/deliverables/*.json')
    print(f"Found {len(deliv_files)} deliverable files to process")
    
    existing_records = table.all()
    existing_ids = {record['fields'].get('deliverableId'): record['id'] 
                   for record in existing_records 
                   if 'deliverableId' in record['fields']}
    
    updated_count = created_count = skipped_count = 0
    
    for file_path in deliv_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Filter out non-standard fields
            filtered_data = {k: v for k, v in data.items() if k in standard_fields}
            
            deliv_id = filtered_data.get('deliverableId')
            if not deliv_id:
                print(f"Warning: Skipping file {file_path} - missing deliverableId")
                skipped_count += 1
                continue
            
            if deliv_id in existing_ids:
                table.update(existing_ids[deliv_id], filtered_data)
                print(f"Updated deliverable: {deliv_id}")
                updated_count += 1
            else:
                table.create(filtered_data)
                print(f"Created new deliverable: {deliv_id}")
                created_count += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            skipped_count += 1
    
    print(f"\nCompleted Deliverables:")
    print(f"  - Created: {created_count}")
    print(f"  - Updated: {updated_count}")
    if skipped_count > 0:
        print(f"  - Skipped: {skipped_count}")

def push_validations():
    print("\nProcessing Validations...")
    
    table = api.table(BASE_ID, 'Validations')
    valid_files = glob.glob('data/validations/*.json')
    print(f"Found {len(valid_files)} validation files to process")
    
    existing_records = table.all()
    existing_ids = {record['fields'].get('validationId'): record['id'] 
                   for record in existing_records 
                   if 'validationId' in record['fields']}
    
    updated_count = created_count = skipped_count = 0
    
    for file_path in valid_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            valid_id = data.get('validationId')
            if not valid_id:
                print(f"Warning: Skipping file {file_path} - missing validationId")
                skipped_count += 1
                continue
            
            if valid_id in existing_ids:
                table.update(existing_ids[valid_id], data)
                print(f"Updated validation: {valid_id}")
                updated_count += 1
            else:
                table.create(data)
                print(f"Created new validation: {valid_id}")
                created_count += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            skipped_count += 1
    
    print(f"\nCompleted Validations:")
    print(f"  - Created: {created_count}")
    print(f"  - Updated: {updated_count}")
    if skipped_count > 0:
        print(f"  - Skipped: {skipped_count}")

def main():
    try:
        push_swarms()
        push_services()
        push_collaborations()
        push_specifications()
        push_messages()
        push_news()
        push_deliverables()
        push_validations()
        print("\nAll data has been pushed successfully!")
    except Exception as e:
        print(f"Error during push: {str(e)}")

if __name__ == '__main__':
    main()
