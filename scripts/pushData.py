import os
from dotenv import load_dotenv
from pyairtable import Api
import json
import glob

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

def push_collaborations():
    print("\nProcessing Collaborations...")
    
    # Get the table
    table = api.table(BASE_ID, 'Collaborations')
    
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
            
            collab_id = data.get('collaborationId')
            if not collab_id:
                print(f"Warning: Skipping file {file_path} - missing collaborationId")
                skipped_count += 1
                continue
            
            # If record exists, update it
            if collab_id in existing_ids:
                table.update(existing_ids[collab_id], data)
                print(f"Updated collaboration: {collab_id}")
                updated_count += 1
            # If record is new, create it
            else:
                table.create(data)
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

def main():
    try:
        push_collaborations()
        print("\nAll data has been pushed successfully!")
    except Exception as e:
        print(f"Error during push: {str(e)}")

if __name__ == '__main__':
    main()
