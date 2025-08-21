from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from datetime import datetime
from controllers.auth import hash_password, verify_password, create_access_token, decode_access_token
from config.mongo import db
from middlewares.auth_required import auth_required
from bson import ObjectId

router = APIRouter(tags=["Authentication"])

class UserCreate(BaseModel):
    firstName: str
    lastName: str
    email: str
    password: str
    phone: str
    experience: str


class UserLogin(BaseModel):
    email: str
    password: str


@router.post("/signup")
async def signup(user: UserCreate):
    try:
        collection = db['users']
        existing_user = await collection.find_one({"email": user.email})
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        user_data = {
            "first_name": user.firstName,
            "last_name": user.lastName,
            "email": user.email,
            "password": hash_password(user.password),
            "phone": user.phone,
            "experience": user.experience,
            "created_at": datetime.utcnow()
        }

        result = await collection.insert_one(user_data)
        
        if not result.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to create user")

        token = create_access_token({"user_id": str(result.inserted_id)})
        
        return {
            "message": "User created successfully",
            "access_token": token,
            "user_id": str(result.inserted_id)
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(user: UserLogin):
    try:
        collection = db['users']
        db_user = await collection.find_one({"email": user.email})
        
        if not db_user or not verify_password(user.password, db_user["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token({"user_id": str(db_user["_id"])})
        
        return {
            "access_token": token,
            "user_id": str(db_user["_id"])
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify")
async def verify_token(user_id: str = Depends(auth_required)):
    try:
        collection = db['users']
        user = await collection.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Remove sensitive data
        user.pop("password", None)
        user["_id"] = str(user["_id"])
        
        return {
            "verified": True,
            "user": user
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



