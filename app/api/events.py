from fastapi import APIRouter, Request
from api.graph import build_graph
from api.models.state import State
state: State = {
            "mode": "evaluation",
            "file_path": "https://ejgpdgbiylcirxusmcbu.supabase.co/storage/v1/object/public/hackathon-files/submissions/20250820_183209_8b995fdc-7fd9-4abd-8edf-76a377a74271.pptx",
            "content": "AI Hackathon focused on startups and innovation",
            "output": None
        }
router = APIRouter()

@router.post("/events")
async def create_event(state: State, req: Request):
    req_body = await req.json()
    print("Request Body:", req_body)

    app = build_graph()
    res = await app.ainvoke(req_body)

    return res
