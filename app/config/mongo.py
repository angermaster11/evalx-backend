from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# Get credentials from env
username = os.getenv("MONGODB_USERNAME", "reva123")
password = os.getenv("MONGODB_PASSWORD", "Arzoo@2005")

# Create encoded connection string
encoded_username = quote_plus(username)
encoded_password = quote_plus(password)
MONGO_URI = f"mongodb+srv://{encoded_username}:{encoded_password}@anger.vej98ud.mongodb.net/?retryWrites=true&w=majority&appName=anger"
DB_NAME = os.getenv("MONGODB_DB")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]