from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from controllers.auth import decode_access_token

security = HTTPBearer()

async def auth_required(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        # Verify token and get user_id
        payload = decode_access_token(token)  # Implement your token verification
        if not payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
            
        user_id = payload.get('user_id')
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User ID not found in token"
            )
            
        return user_id
        
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )
