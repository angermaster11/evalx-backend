from fastapi import APIRouter, Depends, HTTPException
from config.mongo import db
from middlewares.auth_required import auth_required
from bson import ObjectId

router = APIRouter()

def serialize_document(doc):
    if isinstance(doc, list):
        return [serialize_document(item) for item in doc]
    elif isinstance(doc, dict):
        return {k: serialize_document(v) for k, v in doc.items()}
    elif isinstance(doc, ObjectId):
        return str(doc)
    else:
        return doc

@router.get("/hackathons/your")
async def get_your_hackathons(user_id: str = Depends(auth_required)):
    hackathons = await db['events'].find({"created_by": user_id}).to_list(length=100)
    return {"hackathons": serialize_document(hackathons)}

@router.get("/registration/{hack_id}")
async def get_registration(hack_id: str, user_id: str = Depends(auth_required)):
    try:
        teams = db['teams']
        registration = await teams.find({"hack_id": hack_id}).to_list(length=100)

        if not registration:
            raise HTTPException(status_code=404, detail="No registrations found")

        for reg in registration:
            submission = await db['submissions'].find({
                "team_id": str(reg.get("_id")),  # or reg['team_id']
                "hack_id": hack_id
            }).to_list(length=100)
            reg['submissions'] = serialize_document(submission)

        return {"registration": serialize_document(registration)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get('/hackathon/registered')
async def get_registered_hackathons(user_id: str = Depends(auth_required)):
    event = []
    try:
        
        teams = db['teams']
        team_data  = await teams.find({"members.user_id": user_id}).to_list(length=100)
        for team in team_data:
            hack_id = team.get("hack_id")
            events = await db['events'].find_one({'hack_id' : hack_id})
            event.append(events)
        if not team_data:
            raise HTTPException(status_code=404, detail="No team found")
        return {
            "hackathons": serialize_document(event)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


