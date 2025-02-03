import os
from pyairtable import Api
import json

# Get API key from environment variable
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
if not AIRTABLE_API_KEY:
    raise ValueError("AIRTABLE_API_KEY environment variable is required")

# Initialize Airtable API
api = Api(AIRTABLE_API_KEY)

# Configure your base ID and table name
BASE_ID = 'YOUR_BASE_ID'  # Replace with actual base ID
TABLE_NAME = 'Swarms'     # Replace with actual table name

# Get the table
table = api.table(BASE_ID, TABLE_NAME)

# Fetch all records
records = table.all()

# Create output directory if it doesn't exist
os.makedirs('data/swarms', exist_ok=True)

# Process and save records
def save_records():
    # Save full data
    with open('data/swarms/all.json', 'w') as f:
        json.dump(records, f, indent=2)
    
    # Save simplified data (just fields)
    simplified_records = [record['fields'] for record in records]
    with open('data/swarms/simplified.json', 'w') as f:
        json.dump(simplified_records, f, indent=2)
    
    # Save ID mapping
    id_mapping = {record['id']: record['fields'] for record in records}
    with open('data/swarms/by_id.json', 'w') as f:
        json.dump(id_mapping, f, indent=2)

if __name__ == '__main__':
    save_records()
    print("Swarm data has been fetched and saved successfully!")
