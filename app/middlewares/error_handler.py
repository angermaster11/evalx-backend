from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Union

async def error_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )