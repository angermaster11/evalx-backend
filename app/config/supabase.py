from supabase import create_async_client,Client
from dotenv import load_dotenv
import os

load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE URL AND KEY ARE MISSING ")

async def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Missing SUPABASE env variables")
    return await create_async_client(SUPABASE_URL, SUPABASE_KEY)

