from fastapi import FastAPI,HTTPException
from routes.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware
from routes.hackathon import router as hackathon_router
from middlewares.error_handler import error_handler
from routes.events import router as events_router
from api.events import router as events_api_router
from api.nodes.github import router as github_api_router
from routes.interview import router as interview_router
import uvicorn

# making instance of FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Error handling middleware
app.middleware("http")(error_handler)
app.include_router(interview_router, prefix="/interview", tags=["interview"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(events_router, prefix="/events", tags=["events"])
app.include_router(hackathon_router, prefix="/hackathons", tags=["hackathons"])
app.include_router(events_api_router, tags=["api-events"])
app.include_router(github_api_router, prefix="/github", tags=["github"])


@app.get("/")
def read_root():
    return {
        "ping": "Yes, The server is ready"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
