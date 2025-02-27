import uuid
import os

def generate_unique_name() -> str:
    return f"temp_{uuid.uuid4().hex}"

def cleanup_files(*filenames):
    for fname in filenames:
        try:
            os.remove(fname)
        except Exception as e:
            print(f"Error deleting {fname}: {str(e)}")