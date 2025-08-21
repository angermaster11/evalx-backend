from fastapi import APIRouter, File,HTTPException, UploadFile
import cloudinary
import cloudinary.api
import cloudinary.uploader  


async def upload_images(file: UploadFile):
    try:
        # Upload the file to cloudinary
        result = cloudinary.uploader.upload(
            file.file,
            folder="hackathon_submissions"
        )
        
        return {
            "url": result.get("secure_url"),
            "public_id": result.get("public_id")
        }
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return None