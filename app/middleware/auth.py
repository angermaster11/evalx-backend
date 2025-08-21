from fastapi import HTTPException
import jwt
from config.settings import settings

async def auth_required(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get('user_id')
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
            
        return user_id
        
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")