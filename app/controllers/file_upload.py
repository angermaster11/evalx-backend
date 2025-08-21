from fastapi import UploadFile, HTTPException
from config.supabase import get_supabase_client
import uuid
from datetime import datetime
import os
import shutil

async def upload_file_to_supabase(file: UploadFile, folder: str = "submissions") -> str:
    # Create a temp directory if it doesn't exist
    temp_dir = os.path.join(os.getcwd(), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Generate unique temp file path
    temp_file_path = os.path.join(temp_dir, f"temp_{uuid.uuid4().hex}")
    
    try:
        # Save uploaded file to temp location
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file extension and generate unique name
        file_ext = file.filename.split('.')[-1].lower()
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4()}.{file_ext}"
        file_path = f"{folder}/{unique_filename}"

        # Get Supabase client
        supabase = await get_supabase_client()

        # Upload file to Supabase
        with open(temp_file_path, "rb") as f:
            response = await supabase.storage.from_('hackathon-files').upload(
                path=file_path,
                file=f,
                file_options={"content-type": file.content_type}
            )

        if not response:
            raise HTTPException(status_code=500, detail="Failed to upload to Supabase")

        # Get public URL - make sure to await it
        file_url = await supabase.storage.from_('hackathon-files').get_public_url(file_path)
        
        return file_url

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"File upload error: {str(e)}"
        )
    finally:
        # Clean up: Close file handle and remove temp file
        file.file.close()
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass