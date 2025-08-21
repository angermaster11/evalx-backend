from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends,Request
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from config.mongo import db
from controllers.cloudinary import upload_images
from controllers.file_upload import upload_file_to_supabase
from bson import ObjectId
import random
import string
from middlewares.auth_required import auth_required
from datetime import datetime
import json
import traceback
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

from dotenv import load_dotenv
load_dotenv()

router = APIRouter(tags=["Hackathons"])

class Field(BaseModel):
    field_name: str
    type: str

class Round(BaseModel):
    round_name: str
    fields: List[Field]

class FAQ(BaseModel):
    question: str
    answer: str

class TeamMember(BaseModel):
    email: str
    role: str

class Team(BaseModel):
    team_id: str
    team_name: str
    team_code: str
    members: List[TeamMember]
    hack_id: str

class Hackathon(BaseModel):
    hack_id: str
    name: str
    date: str
    time: str
    created_by : Optional[str] = None
    duration: str
    description: Optional[str] = None
    summary: Optional[str] = None
    faqs: Optional[List[FAQ]] = []
    rounds: Optional[List[Round]] = []
    banner_url: Optional[str] = None
    logo_url: Optional[str] = None
    banner_filename: Optional[str] = None
    logo_filename: Optional[str] = None
    min_members: int = 1
    max_members: int = 4
    registration_open: bool = True
    teams: List[str] = []

@router.post("/create")
async def create_hackathon(
    hack_id: str = Form(...),
    name: str = Form(...),
    date: str = Form(...),
    time: str = Form(...),
    user_id: str = Depends(auth_required),
    duration: str = Form(...),
    description: str = Form(None),
    summary: str = Form(None),
    faqs: str = Form(None),
    rounds: str = Form(None),
    banner: UploadFile = File(None),
    logo: UploadFile = File(None),
):
    try:
        # Parse FAQs and rounds if provided
        faq_list = []
        rounds_list = []
        
        if faqs:
            try:
                faq_list = json.loads(faqs)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid FAQs format")
                
        if rounds:
            try:
                rounds_list = json.loads(rounds)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid rounds format")

        # Validate required fields
        if not all([hack_id, name, date, time, duration]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        hackathon_data = {
            "hack_id": hack_id,
            "name": name,
            "date": date,
            "time": time,
            "duration": duration,
            "description": description,
            "summary": summary,
            "created_by": user_id,
            "faqs": faq_list,
            "rounds": rounds_list,
            "banner_filename": banner.filename if banner else None,
            "logo_filename": logo.filename if logo else None,
        }

        # Upload images to Cloudinary if provided
        if banner:
            banner_upload = await upload_images(banner)
            if not banner_upload.get("url"):
                raise HTTPException(status_code=500, detail="Failed to upload banner")
            hackathon_data["banner_url"] = banner_upload["url"]

        if logo:
            logo_upload = await upload_images(logo)
            if not logo_upload.get("url"):
                raise HTTPException(status_code=500, detail="Failed to upload logo")
            hackathon_data["logo_url"] = logo_upload["url"]

        # Add to database
        collection = db['events']
        result = await collection.insert_one(hackathon_data)
        
        if not result.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to create hackathon")

        return JSONResponse(
            status_code=201,
            content={
                "message": "Hackathon created successfully",
                "hack_id": hack_id
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all")
async def get_all_hackathons():
    try:
        collection = db['events']
        hackathons = await collection.find({}).to_list(length=None)
        
        # Convert ObjectId to string for JSON serialization
        for hackathon in hackathons:
            hackathon["_id"] = str(hackathon["_id"])
            
        return {"hackathons": hackathons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{hack_id}")
async def get_hackathon(hack_id: str, user_id: str = Depends(auth_required)):
    try:
        status = False
        collection = db['events']
        hackathon = await collection.find_one({"hack_id": hack_id})
        
        if not hackathon:
            raise HTTPException(status_code=404, detail="Hackathon not found")
            
        hackathon["_id"] = str(hackathon["_id"])
        if hackathon["created_by"] == user_id:
            status = True
        hackathon["is_creator"] = status
        return hackathon
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def generate_team_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@router.post("/teams/create")
async def create_team(
    hack_id: str = Form(...),
    team_name: str = Form(...),
    user_id: str = Depends(auth_required)
):
    try:
        # Get hackathon details
        events_collection = db['events']
        teams_collection = db['teams']
        users_collection = db['users']

        hackathon = await events_collection.find_one({"hack_id": hack_id})
        if not hackathon:
            raise HTTPException(status_code=404, detail="Hackathon not found")

        # Check if user already has a team in this hackathon
        existing_team = await teams_collection.find_one({
            "hack_id": hack_id,
            "members.user_id": user_id
        })
        if existing_team:
            raise HTTPException(status_code=400, detail="Already registered in a team")

        # Get user details
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create team with _id
        team_id = ObjectId()
        team_code = generate_team_code()
        team_data = {
            "_id": team_id,
            "hack_id": hack_id,
            "team_name": team_name,
            "team_code": team_code,
            "members": [{
                "user_id": user_id,
                "email": user["email"],
                "name": f"{user['first_name']} {user['last_name']}",
                "role": "leader"
            }],
            "created_at": datetime.utcnow()
        }

        result = await teams_collection.insert_one(team_data)
        if not result.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to create team")

        return {
            "message": "Team created successfully",
            "team_code": team_code,
            "team_name": team_name,
            "team_id": str(team_id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/teams/join")
async def join_team(
    hack_id: str = Form(...),
    team_code: str = Form(...),
    user_id: str = Depends(auth_required)
):
    try:
        teams_collection = db['teams']
        users_collection = db['users']
        events_collection = db['events']

        # Check if hackathon exists
        hackathon = await events_collection.find_one({"hack_id": hack_id})
        if not hackathon:
            raise HTTPException(status_code=404, detail="Hackathon not found")

        # Check if team exists
        team = await teams_collection.find_one({
            "hack_id": hack_id,
            "team_code": team_code
        })
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Check if user already has a team
        existing_team = await teams_collection.find_one({
            "hack_id": hack_id,
            "members.user_id": user_id
        })
        if existing_team:
            raise HTTPException(status_code=400, detail="Already registered in a team")

        # Check team size limit
        if len(team["members"]) >= hackathon.get("max_members", 4):
            raise HTTPException(status_code=400, detail="Team is full")

        # Get user details
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Add member to team
        result = await teams_collection.update_one(
            {"_id": team["_id"]},
            {"$push": {
                "members": {
                    "user_id": user_id,
                    "email": user["email"],
                    "name": f"{user['first_name']} {user['last_name']}",
                    "role": "member"
                }
            }}
        )

        if not result.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to join team")

        return {
            "message": "Successfully joined team",
            "team_name": team["team_name"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/teams/{hack_id}")
async def get_team(hack_id: str, user_id: str = Depends(auth_required)):
    try:
        teams_collection = db['teams']
        team = await teams_collection.find_one({
            "hack_id": hack_id,
            "members.user_id": user_id
        })

        if not team:
            return {"registered": False}

        team["_id"] = str(team["_id"])
        return {
            "registered": True,
            "team": team
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{hack_id}/registration")
async def update_registration_status(
    hack_id: str,
    status: bool = Form(...)
):
    try:
        collection = db['events']
        result = await collection.update_one(
            {"hack_id": hack_id},
            {"$set": {"registration_open": status}}
        )
        
        if not result.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to update registration status")
            
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Registration {'opened' if status else 'closed'} successfully"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rounds/submit")
async def submit_round(
    hack_id: str = Form(...),
    round_index: int = Form(...),
    team_id: str = Form(...),
    submissions: str = Form(...),
    user_id: str = Depends(auth_required)
):
    try:
        # Parse submissions JSON
        try:
            submissions_data = json.loads(submissions)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid submissions format")

        # Validate team existence
        teams_collection = db['teams']
        team = await teams_collection.find_one({"_id": ObjectId(team_id)})
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Check if already submitted
        submissions_collection = db['submissions']
        existing_submission = await submissions_collection.find_one({
            "hack_id": hack_id,
            "round_index": round_index,
            "team_id": team_id
        })
        if existing_submission:
            raise HTTPException(status_code=400, detail="Round already submitted")

        # Create submission
        url = submissions_data['url'] if 'url' in submissions_data else "none"

        submission_data = {
            "hack_id": hack_id,
            "round_index": round_index,
            "team_id": team_id,
            "submissions": submissions_data,
            "submitted_by": user_id,
            "submitted_at": datetime.utcnow()
        }
        
        result = await submissions_collection.insert_one(submission_data)
        if not result.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to save submission")

        return {"message": "Submission successful","url" : url}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rounds/status/{hack_id}")
async def get_rounds_status(
    hack_id: str,
    user_id: str = Depends(auth_required)
):
    try:
        # Get user's team
        teams_collection = db['teams']
        submissions_collection = db['submissions']
        files_collection = db['file_submissions']
        
        team = await teams_collection.find_one({
            "hack_id": hack_id,
            "members.user_id": user_id
        })
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
            
        # Get all submissions with file details
        submissions = await submissions_collection.find({
            "hack_id": hack_id,
            "team_id": str(team["_id"])
        }).to_list(None)
        
        round_status = {}
        for submission in submissions:
            # Get associated files
            files = []
            if "file_references" in submission:
                file_docs = await files_collection.find({
                    "_id": {"$in": [ObjectId(ref) for ref in submission["file_references"]]}
                }).to_list(None)
                files = [{"field": f["field_name"], "url": f["file_url"]} for f in file_docs]

            round_status[submission["round_index"]] = {
                "submitted": True,
                "submitted_at": submission["submitted_at"],
                "files": files,
                "data": submission["submissions"]
            }
            
        return round_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-file")  # Changed from /upload/file
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(auth_required)
):
    try:
        # Upload file to Supabase
        file_url = await upload_file_to_supabase(file)
        
        # Store file reference in database
        files_collection = db['file_submissions']
        file_data = {
            "file_name": file.filename,
            "file_url": file_url,
            "uploaded_by": user_id,
            "uploaded_at": datetime.utcnow(),
            "file_type": file.content_type
        }
        
        result = await files_collection.insert_one(file_data)
        
        if not result.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to save file reference")

        return {
            "url": file_url,
            "filename": file.filename
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {str(e)}"
        )

@router.get("/registered")
async def get_registered_hackathons(user_id: str = Depends(auth_required)):
    try:
        # Validate user_id
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Get user's teams
        teams_collection = db['teams']
        teams = await teams_collection.find({
            "members.user_id": user_id
        }).to_list(None)

        # Return empty list if no teams found
        if not teams:
            return []

        # Get hackathon IDs
        hack_ids = [team["hack_id"] for team in teams]

        # Get hackathon details
        events_collection = db['events']
        hackathons = []

        # Fetch and process each hackathon
        for hack_id in hack_ids:
            try:
                hackathon = await events_collection.find_one({"hack_id": hack_id})
                if hackathon:
                    # Find corresponding team
                    team = next((t for t in teams if t["hack_id"] == hack_id), None)
                    if team:
                        # Convert ObjectId to string
                        hackathon["_id"] = str(hackathon["_id"])
                        team["_id"] = str(team["_id"])
                        
                        # Add team info
                        hackathon["team"] = {
                            "team_name": team.get("team_name", "Unknown Team"),
                            "team_code": team.get("team_code"),
                            "members": team.get("members", []),
                            "_id": str(team["_id"])
                        }
                        hackathons.append(hackathon)
            except Exception as e:
                print(f"Error processing hackathon {hack_id}: {str(e)}")
                continue

        return hackathons

    except Exception as e:
        print(f"Error in get_registered_hackathons: {str(e)}")
        print(traceback.format_exc())  # Print full traceback for debugging
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/round2/{hack_id}")
async def get_round2_submissions(hack_id: str, user_id: str = Depends(auth_required)):
    try:
        
        teams_collection = db['github_evaluations']
        data = await teams_collection.find({
            "hack_id": hack_id
        }).to_list(None)

        if not data:
            return []

        result = []
        for item in data:
            if "result" in item and item["result"]:
                metrics = item["result"]
                
                # Safely extract values - handle both nested and direct values
                def get_metric_value(metrics, key, default=0):
                    value = metrics.get(key, {})
                    if isinstance(value, dict):
                        # Handle nested format: {"$numberDouble": "74.0"}
                        if "$numberDouble" in value:
                            return float(value["$numberDouble"])
                        # Handle nested format: {"$numberInt": "38"}
                        elif "$numberInt" in value:
                            return int(value["$numberInt"])
                        else:
                            return default
                    else:
                        # Handle direct values: 74.0 or "74.0"
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            return default
                
                # Extract metric values
                logic_val = get_metric_value(metrics, "logic", 0)
                relevance_val = get_metric_value(metrics, "relevance", 0)
                style_val = get_metric_value(metrics, "style", 0)
                structure_val = get_metric_value(metrics, "structure_score", 0)
                plagiarism_val = get_metric_value(metrics, "plagiarism_percent", 0)
                pylint_val = get_metric_value(metrics, "pylint_score", 0)
                
                # Get code_chunks_count safely
                code_chunks = metrics.get("code_chunks_count", {})
                if isinstance(code_chunks, dict) and "$numberInt" in code_chunks:
                    code_chunks_count = int(code_chunks["$numberInt"])
                else:
                    code_chunks_count = int(code_chunks) if str(code_chunks).isdigit() else 0
                
                # Get complexity issues
                complexity_issues = metrics.get("complexity_issues", [])
                complexity_issues_count = len(complexity_issues) if isinstance(complexity_issues, list) else 0
                
                # Get structure analysis
                structure_analysis = metrics.get("structure_analysis", {})
                
                # Calculate scores with multipliers
                logic_score = int(logic_val * 0.4)
                relevance_score = int(relevance_val * 0.3)
                style_score = int(style_val * 0.2)
                structure_score = int(structure_val * 0.1)
                
                # Calculate complexity penalty
                complexity_penalty = min(complexity_issues_count * 2, 10)
                
                # Final score calculation
                final_score = max(0, min(100, (
                    logic_score + relevance_score + style_score + 
                    structure_score - complexity_penalty
                )))
                
                metrics_json = {
                    "team_code": item.get("team_code", ""),
                    "hack_id": item.get("hack_id", ""),
                    "scores": {
                        "logic": logic_score,
                        "relevance": relevance_score,
                        "style": style_score,
                        "structure": structure_score,
                        "complexity_penalty": complexity_penalty,
                        "final_score": final_score
                    },
                    "detailed_metrics": {
                        "plagiarism_percent": int(plagiarism_val),
                        "pylint_score": int(pylint_val),
                        "code_chunks_count": code_chunks_count,
                        "complexity_issues_count": complexity_issues_count,
                        "has_readme": structure_analysis.get("has_readme", False),
                        "has_tests": structure_analysis.get("has_tests", False)
                    }
                }
                
                result.append(metrics_json)
        
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing round2 submissions: {str(e)}")



    return {"response": response}
