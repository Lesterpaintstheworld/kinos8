import os
import sys
import codecs
import json
from dotenv import load_dotenv
from pyairtable import Api

# Force UTF-8 encoding for stdin/stdout/stderr
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
if sys.stdin.encoding != 'utf-8':
    sys.stdin = codecs.getreader('utf-8')(sys.stdin.buffer, 'strict')

# Set default encoding to UTF-8
import locale
locale.getpreferredencoding = lambda: 'UTF-8'

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
    'Messages': 'messageId',
    'Specifications': 'specificationId',
    'Deliverables': 'deliverableId',
    'Validations': 'validationId'
}

def fetch_and_save_table(table_name, id_field):
    print(f"\nProcessing {table_name}...")
    
    # Get the table
    table = api.table(BASE_ID, table_name)
    
    # Fetch all records
    print(f"Fetching records from {table_name} table...")
    records = table.all()
    print(f"Found {len(records)} records in {table_name}")
    
    if len(records) > 0:
        # Debug: Print first record fields
        print(f"Available fields in first record: {list(records[0]['fields'].keys())}")
    
    # Create output directory if it doesn't exist
    directory = f"data/{table_name.lower()}"
    os.makedirs(directory, exist_ok=True)
    
    # Save individual files
    saved_count = 0
    skipped_count = 0
    for record in records:
        record_id = record['fields'].get(id_field)
        if not record_id:
            print(f"Warning: Record missing {id_field}. Available fields: {list(record['fields'].keys())}")
            skipped_count += 1
            continue
            
        filename = f"{directory}/{record_id}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(record['fields'], f, indent=2, ensure_ascii=False)
        saved_count += 1
    
    print(f"Completed {table_name}:")
    print(f"  - Saved: {saved_count} files")
    if skipped_count > 0:
        print(f"  - Skipped: {skipped_count} records (missing ID)")

def main():
    for table_name, id_field in TABLES.items():
        try:
            fetch_and_save_table(table_name, id_field)
        except Exception as e:
            print(f"Error processing {table_name}: {str(e)}")

if __name__ == '__main__':
    main()
    print("All data has been fetched and saved successfully!")
