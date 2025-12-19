import hashlib
import os
from datetime import datetime

from fastapi import UploadFile

UPLOAD_DIR = "static/upload"

def get_file_md5(file_path: str) -> str:
    """Calculate MD5 of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_content_md5(content: bytes) -> str:
    """Calculate MD5 of bytes content."""
    return hashlib.md5(content).hexdigest()

async def save_upload_file(file: UploadFile) -> dict:
    """
    Save uploaded file to static/upload/YYYY-MM-DD/
    Returns a dict with file info.
    """
    # Create directory based on current date
    now = datetime.now()
    date_path = now.strftime("%Y-%m-%d")
    save_dir = os.path.join(UPLOAD_DIR, date_path)
    os.makedirs(save_dir, exist_ok=True)

    # Read content to calculate MD5 and save
    content = await file.read()
    md5 = get_content_md5(content)
    
    # Reset cursor for saving (though we have content in memory, we can write bytes directly)
    # If file is huge, this might be memory intensive. 
    # For better memory usage, we could read chunk by chunk, update md5, and write to temp file.
    # But for simplicity and assuming reasonable file sizes for this demo:
    
    filename = file.filename
    file_path = os.path.join(save_dir, filename)
    
    # Handle duplicate filenames in same directory if needed, 
    # but requirement says "upload/" then by date. 
    # If same name exists, we overwrite or rename? 
    # Let's just write it.
    
    with open(file_path, "wb") as f:
        f.write(content)
        
    file_size = len(content)
    
    # URL construction (relative path)
    url = f"/{save_dir}/{filename}"
    
    return {
        "path": file_path,
        "url": url,
        "size": file_size,
        "name": filename,
        "md5": md5,
        "contentType": file.content_type
    }
