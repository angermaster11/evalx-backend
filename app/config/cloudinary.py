from fastapi import FastAPI, File, UploadFile, HTTPException
import cloudinary
import cloudinary.api
import cloudinary.uploader
from dotenv import load_dotenv
import os 

load_dotenv()

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")

cloudinary.config(
    cloud_name = CLOUDINARY_CLOUD_NAME,
    api_key = CLOUDINARY_API_KEY,
    api_secret = CLOUDINARY_API_SECRET
)