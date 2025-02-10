import json
import glob
from datetime import datetime, timedelta

def update_message_timestamps():
    # Start time at 12:01
    current_time = datetime.strptime("12:01", "%H:%M")
    
    # Order of message files
    order = ["23", "58", "12", "47", "m20_2024_01_22", "m25_2024_01_22", "m21_2024_01_22", 
            "m24_2024_01_22", "m23_2024_01_22", "16", "20", "18", "22", "24", "53", "55", 
            "57", "59", "61", "63", "65", "67", "70", "75", "72", "79", "82", 
            "9d6c9083-3e37-4c0a-8864-c3d5b7ff5f48", "b5dca6a8-db03-4373-ae23-012def5c6ac1",
            "c1c8c8e8-24e0-4c9c-a357-c7f76e7d3381", "c1c8c8e8-24e0-4c9c-a357-c7f76e7d3382",
            "m10_2024_01_22", "m11_2024_01_22", "m14_2024_01_22", "m15_2024_01_22",
            "m8_2024_01_22", "m6_2024_01_22", "b5dca6a8-db03-4373-ae23-012def5c6ac4",
            "pw-001-hardware-v1-proposal", "pw-003-hardware-v1-devkit", "m26_2024_01_22",
            "m27_2024_01_22", "62", "64", "66", "69", "68", "71", "74", "73", "77", "76",
            "78", "81", "80", "83", "pw-002-hardware-v1-feedback", "pw-004-hardware-v1-parts",
            "pw-005-hardware-v1-specs", "21", "56", "48", "2-", "4-", "6", "8", "10", "2",
            "4", "25", "60", "19", "54", "17", "52", "9d6c9083-3e37-4c0a-8864-c3d5b7ff5f47",
            "b5dca6a8-db03-4373-ae23-012def5c6ac2", "e31d3c95-8e7a-4bfd-9e92-43958a587d1f",
            "e31d3c95-8e7a-4bfd-9e92-43958a587d2f", "d7e8f9a0-b1c2-4d3e-a4b5-c6d7e8f9a0b1",
            "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6", "e7f8d9c0-a1b2-c3d4-e5f6-g7h8i9j0k1l2",
            "m13_2024_01_22", "m17_2024_01_22", "m16_2024_01_22", "m7_2024_01_22",
            "m5_2024_01_22", "m9_2024_01_22", "m18_2024_01_22", "c861e426-af70-4768-9ce3-0395aac72cc8",
            "69689882-f683-419d-bb00-74ef2391c89e", "33488c9f-aee3-4bd7-997f-dab7aca5287b",
            "04cf26dc-35f8-4643-9ea4-f3cb2ad5bcb4", "3dcef21b-7097-44b4-adaf-0e8d4d635dc3",
            "bce0b7ae-ae41-4e77-a73b-a9dd8a77db90", "m30_2024_01_22", "m31_2024_01_22",
            "m32_2024_01_22", "m33_2024_01_22", "m34_2024_01_22", "m35_2024_01_22",
            "m36_2024_01_22", "m37_2024_01_22", "m38_2024_01_22", "m39_2024_01_22"]

    for message_id in order:
        # Find the message file
        message_files = glob.glob(f'data/messages/{message_id}.json')
        if message_files:
            file_path = message_files[0]
            try:
                # Read the message
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Update timestamp with current time
                date = data['timestamp'].split(' ')[0] if ' ' in data['timestamp'] else data['timestamp']
                data['timestamp'] = f"{date} {current_time.strftime('%H:%M')}"
                
                # Write back to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                print(f"Updated {message_id} with timestamp {data['timestamp']}")
                
                # Increment time by 1 minute
                current_time += timedelta(minutes=1)
                
            except Exception as e:
                print(f"Error processing {message_id}: {e}")
        else:
            print(f"Message file not found for ID: {message_id}")

def main():
    print("Updating message timestamps...")
    update_message_timestamps()
    print("Done!")

if __name__ == '__main__':
    main()
