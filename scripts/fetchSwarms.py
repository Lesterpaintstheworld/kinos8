import os
from dotenv import load_dotenv
from pyairtable import Api
import json

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

# Configure table names and their corresponding ID fields
TABLES = {
    'Swarms': 'swarmId',
    'News': 'newsId',
    'Services': 'serviceId',
    'Collaborations': 'collaborationId',
    'Messages': 'messageId'
}

def fetch_and_save_table(table_name, id_field):
    # Get the table
    table = api.table(BASE_ID, table_name)
    
    # Fetch all records
    records = table.all()
    
    # Create output directory if it doesn't exist
    directory = f"data/{table_name.lower()}"
    os.makedirs(directory, exist_ok=True)
    
    # Save individual files
    for record in records:
        record_id = record['fields'].get(id_field)
        if record_id:
            filename = f"{directory}/{record_id}.json"
            with open(filename, 'w') as f:
                json.dump(record['fields'], f, indent=2)

def main():
    for table_name, id_field in TABLES.items():
        print(f"Fetching {table_name}...")
        fetch_and_save_table(table_name, id_field)
        print(f"Completed {table_name}")

if __name__ == '__main__':
    main()
    print("All data has been fetched and saved successfully!")
