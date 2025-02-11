import sys
import codecs

def check_encoding(file_path):
    with open(file_path, 'rb') as f:
        content = f.read()
        for i, byte in enumerate(content):
            if byte > 127:
                print(f"Found special character at position {i}: byte {hex(byte)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_encoding.py <file_path>")
        sys.exit(1)
    check_encoding(sys.argv[1])
