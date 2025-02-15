import os
import glob
import json
from datetime import datetime

def get_files_sorted_by_date(directory):
    """Get files from directory sorted by createdAt field in JSON"""
    files = []
    for file_path in glob.glob(f"{directory}/*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                created_at = data.get('createdAt', '')
                files.append((file_path, created_at))
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue
    
    # Sort by date descending and return just the paths
    return [f[0] for f in sorted(files, key=lambda x: x[1], reverse=True)]

def get_context_files():
    """Get list of files for global conversation context"""
    context_files = []
    
    # Get all swarms
    context_files.extend(glob.glob("data/swarms/*.json"))
    
    # Get all services
    context_files.extend(glob.glob("data/services/*.json"))
    
    # Get all news
    context_files.extend(glob.glob("data/news/*.json"))
    
    # Get all collaborations
    context_files.extend(glob.glob("data/collaborations/*.json"))
    
    # Get last 5 deliverables
    deliverables = get_files_sorted_by_date("data/deliverables")
    context_files.extend(deliverables[:5])
    
    # Get last 5 specifications
    specifications = get_files_sorted_by_date("data/specifications")
    context_files.extend(specifications[:5])
    
    return context_files

def main():
    # Get all context files
    files = get_context_files()
    
    # Convert paths to use forward slashes and strip any ./ prefix
    formatted_files = [f.replace('\\', '/').replace('./', '') for f in files]
    
    # Sort alphabetically
    formatted_files.sort()
    
    # Print each file path
    for file_path in formatted_files:
        print(file_path)

if __name__ == "__main__":
    main()
