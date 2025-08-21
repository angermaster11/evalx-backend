# ==========================================
# Advanced GitHub Repo Evaluator
# ==========================================

import os
import git
import subprocess
import json
import tempfile
import shutil
import time
import stat
from typing import Dict, List, Tuple, Any

# ==========================================
# 1️⃣ Clone GitHub Repo
# ==========================================
def clone_repo(github_url: str, repo_folder: str = None) -> str:
    if repo_folder is None:
        repo_folder = tempfile.mkdtemp(prefix="repo_")
    
    if os.path.exists(repo_folder):
        try:
            # Force remove read-only files on Windows
            def remove_readonly(func, path, excinfo):
                os.chmod(path, stat.S_IWRITE)
                func(path)
            
            shutil.rmtree(repo_folder, onerror=remove_readonly)
        except PermissionError:
            print(f"Warning: Could not delete {repo_folder}, using existing directory")
    
    git.Repo.clone_from(github_url, repo_folder)
    return repo_folder

# ==========================================
# 2️⃣ Extract All Code Files
# ==========================================
def get_code_files(repo_path: str, exts: List[str] = None) -> List[str]:
    if exts is None:
        exts = [".py", ".js", ".cpp", ".java", ".c", ".h", ".ts", ".html", ".css", ".md", ".txt"]
    
    code_chunks = []
    for root, _, files in os.walk(repo_path):
        # Skip hidden directories like .git, .venv, etc.
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue
            
        for f in files:
            if any(f.endswith(ext) for ext in exts):
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                        content = file.read()
                        if content.strip():  # Only include non-empty files
                            # Split large files into ~1000 lines chunks
                            lines = content.splitlines()
                            for i in range(0, len(lines), 1000):
                                chunk = "\n".join(lines[i:i+1000])
                                code_chunks.append(f"# FILE: {f} (lines {i+1}-{min(i+1000, len(lines))})\n{chunk}")
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
    return code_chunks

# ==========================================
# 3️⃣ Static Analysis
# ==========================================
def run_static_analysis(repo_path: str) -> Tuple[Any, float, List[Dict]]:
    radon_result = {}
    pylint_score = 0.0
    complexity_issues = []
    
    # Check if radon is available
    try:
        radon_output = subprocess.run(
            ["radon", "cc", repo_path, "-s", "-j"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        if radon_output.returncode == 0:
            radon_result = json.loads(radon_output.stdout)
            
            # Analyze complexity results
            for file_path, functions in radon_result.items():
                for func in functions:
                    if func.get('complexity', 0) > 7:  # High complexity threshold
                        complexity_issues.append({
                            "file": file_path,
                            "function": func.get('name', 'unknown'),
                            "complexity": func.get('complexity', 0),
                            "type": func.get('type', 'unknown')
                        })
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Radon analysis failed: {e}")
        radon_result = {"error": str(e)}
    
    # Check if pylint is available and there are Python files
    py_files = [os.path.join(dp, f) for dp, _, fs in os.walk(repo_path) 
               for f in fs if f.endswith(".py") and not any(part.startswith('.') for part in dp.split(os.sep))]
    if py_files:
        try:
            # Sample a few files for pylint to avoid timeout
            sample_files = py_files[:3] if len(py_files) > 3 else py_files
            pylint_output = subprocess.run(
                ["pylint"] + sample_files + ["--score=y"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            if pylint_output.returncode in [0, 4, 8, 16, 32]:  # Pylint returns various exit codes
                for line in pylint_output.stdout.split("\n"):
                    if "Your code has been rated at" in line:
                        try:
                            pylint_score = float(line.split("Your code has been rated at ")[1].split("/10")[0])
                            break
                        except (IndexError, ValueError):
                            pass
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"Pylint analysis failed: {e}")
    
    return radon_result, pylint_score, complexity_issues

# ==========================================
# 4️⃣ Plagiarism Check
# ==========================================
def run_plagiarism_check(repo_path: str) -> float:
    percent = 0.0
    try:
        result = subprocess.run(
            ["npx", "jscpd", repo_path, "--reporters", "json"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        if result.returncode == 0:
            try:
                plagiarism_data = json.loads(result.stdout)
                percent = plagiarism_data.get('statistics', {}).get('total', {}).get('percentage', 0.0)
            except json.JSONDecodeError:
                # Fallback to text parsing
                for line in result.stdout.split("\n"):
                    if "Total" in line and "%" in line:
                        try:
                            percent = float(line.strip().split("%")[0].split()[-1])
                            break
                        except (IndexError, ValueError):
                            pass
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"Plagiarism check failed: {e}")
    
    return percent

# ==========================================
# 5️⃣ Repository Structure Analysis
# ==========================================
def analyze_repo_structure(repo_path: str) -> Dict:
    structure_analysis = {
        "has_readme": False,
        "has_requirements": False,
        "has_dockerfile": False,
        "has_github_actions": False,
        "has_tests": False,
        "file_count": 0,
        "dir_count": 0
    }
    
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        structure_analysis["dir_count"] += len(dirs)
        structure_analysis["file_count"] += len(files)
        
        for file in files:
            file_lower = file.lower()
            if file_lower in ["readme.md", "readme.txt", "readme"]:
                structure_analysis["has_readme"] = True
            elif file_lower in ["requirements.txt", "pyproject.toml", "setup.py"]:
                structure_analysis["has_requirements"] = True
            elif file_lower == "dockerfile":
                structure_analysis["has_dockerfile"] = True
            elif ".github/workflows" in root.replace("\\", "/"):
                structure_analysis["has_github_actions"] = True
            elif "test" in root.lower() or "tests" in root.lower():
                structure_analysis["has_tests"] = True
    
    return structure_analysis

# ==========================================
# 6️⃣ LLM Evaluation (Logic, Relevance, Style)
# ==========================================
def evaluate_with_llm(project_desc: str, code_chunks: List[str], max_tokens: int = 3000) -> Tuple[float, float, float, List[str]]:
    # Import here to avoid dependency if not using LLM
    try:
        # Try the new import first, fall back to old if needed
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            try:
                from langchain_community.chat_models import ChatOpenAI
            except ImportError:
                from langchain.chat_models import ChatOpenAI
        from langchain.prompts import ChatPromptTemplate
    except ImportError:
        print("LangChain not available. Using default scores.")
        return 50.0, 50.0, 50.0, ["LLM evaluation unavailable - LangChain not installed"]
    
    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY environment variable not set. Using default scores.")
        return 50.0, 50.0, 50.0, ["LLM evaluation skipped - OPENAI_API_KEY not set"]
    
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=api_key)
        logic_scores, relevance_scores, style_scores = [], [], []
        feedback_comments = []
        
        # Limit the number of chunks to avoid excessive API calls
        for i, chunk in enumerate(code_chunks[:5]):  # Evaluate first 5 chunks only
            code_snippet = chunk[:max_tokens]  # truncate if too long
            
            prompt_template = """
You are a hackathon code evaluator. Please analyze this code snippet and provide scores.

PROJECT DESCRIPTION:
{description}

CODE SNIPPET:
{code}

EVALUATION CRITERIA:
1. Logic Quality (0-100): How well does the code implement its intended functionality? Is it efficient and bug-free?
2. Relevance (0-100): How relevant is this code to the project description? Does it align with the project goals?
3. Style & Readability (0-100): How clean, well-structured, and readable is the code? Includes naming, comments, structure.

IMPORTANT: Return ONLY a valid JSON object with this exact structure:
{{
  "logic": 85,
  "relevance": 90,
  "style": 75,
  "feedback": "Brief specific feedback about this code snippet"
}}

Do not include any other text, explanations, or markdown formatting.
"""
            
            try:
                prompt = ChatPromptTemplate.from_template(prompt_template)
                resp = llm.invoke(prompt.format(description=project_desc, code=code_snippet))
                
                # Try to extract JSON from response
                response_text = resp.content.strip()
                
                # Handle cases where response might have extra text
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                data = json.loads(response_text)
                logic_scores.append(data.get("logic", 50))
                relevance_scores.append(data.get("relevance", 50))
                style_scores.append(data.get("style", 50))
                feedback_comments.append(data.get("feedback", "No specific feedback provided"))
                
            except json.JSONDecodeError as e:
                print(f"JSON parsing failed for response: '{resp.content}'. Error: {e}")
                logic_scores.append(50)
                relevance_scores.append(50)
                style_scores.append(50)
                feedback_comments.append(f"LLM response parsing failed: {str(e)}")
            except Exception as e:
                print(f"LLM evaluation failed for chunk {i}: {e}")
                logic_scores.append(50)
                relevance_scores.append(50)
                style_scores.append(50)
                feedback_comments.append(f"Evaluation error: {str(e)}")
        
        # Average all chunks
        if logic_scores:
            logic_avg = sum(logic_scores)/len(logic_scores)
            relevance_avg = sum(relevance_scores)/len(relevance_scores)
            style_avg = sum(style_scores)/len(style_scores)
            return logic_avg, relevance_avg, style_avg, feedback_comments
        else:
            return 50.0, 50.0, 50.0, ["No code chunks evaluated"]
    except Exception as e:
        print(f"LLM initialization failed: {e}")
        return 50.0, 50.0, 50.0, [f"LLM initialization failed: {str(e)}"]

# ==========================================
# 7️⃣ Compute Final Weighted Score
# ==========================================
def compute_final_score(plagiarism: float, logic: float, relevance: float, style: float, 
                       pylint_score: float, structure_score: float) -> float:
    plagiarism_score = (100 - plagiarism) * 0.3
    logic_score = logic * 0.25
    relevance_score = relevance * 0.2
    style_score = style * 0.1
    quality_score = (pylint_score * 10) * 0.1  # Convert 0-10 to 0-100 scale
    structure_bonus = structure_score * 0.05
    
    final_score = (plagiarism_score + logic_score + relevance_score + 
                  style_score + quality_score + structure_bonus)
    return round(final_score, 2)

# ==========================================
# 8️⃣ Generate Comprehensive Feedback
# ==========================================
def generate_feedback(analysis_results: Dict) -> Dict:
    feedback = {
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
        "overall_impression": ""
    }
    
    # Analyze strengths
    if analysis_results["pylint_score"] >= 7.0:
        feedback["strengths"].append("Good code quality with high pylint score")
    if analysis_results["plagiarism_percent"] < 5.0:
        feedback["strengths"].append("Low plagiarism percentage indicates original work")
    if analysis_results["logic"] >= 70:
        feedback["strengths"].append("Strong logical implementation")
    if analysis_results["structure_analysis"]["has_readme"]:
        feedback["strengths"].append("Well-documented with README")
    if analysis_results["structure_analysis"]["has_requirements"]:
        feedback["strengths"].append("Good dependency management")
    
    # Analyze weaknesses
    complexity_issues = analysis_results.get("complexity_issues", [])
    if complexity_issues:
        feedback["weaknesses"].append(f"High complexity in {len(complexity_issues)} functions")
    if analysis_results["pylint_score"] < 5.0:
        feedback["weaknesses"].append("Low code quality score needs improvement")
    if not analysis_results["structure_analysis"]["has_tests"]:
        feedback["weaknesses"].append("No test files detected")
    if analysis_results["style"] < 60:
        feedback["weaknesses"].append("Code style and readability need improvement")
    
    # Generate recommendations
    if complexity_issues:
        feedback["recommendations"].append("Refactor complex functions to improve maintainability")
    if not analysis_results["structure_analysis"]["has_tests"]:
        feedback["recommendations"].append("Add unit tests to ensure code reliability")
    if analysis_results["style"] < 70:
        feedback["recommendations"].append("Improve code formatting and add comments")
    if not analysis_results["structure_analysis"]["has_github_actions"]:
        feedback["recommendations"].append("Consider adding CI/CD with GitHub Actions")
    
    # Overall impression
    final_score = analysis_results["final_score"]
    if final_score >= 85:
        feedback["overall_impression"] = "Excellent project with strong implementation"
    elif final_score >= 70:
        feedback["overall_impression"] = "Good project with some areas for improvement"
    elif final_score >= 50:
        feedback["overall_impression"] = "Average project needing significant improvements"
    else:
        feedback["overall_impression"] = "Project requires major refactoring and improvements"
    
    return feedback

# ==========================================
# 9️⃣ Main Evaluation Function
# ==========================================
def evaluate_repository(github_url: str, project_desc: str) -> Dict[str, Any]:
    # Clone repository
    repo_path = clone_repo(github_url)
    
    try:
        # Extract code files
        code_chunks = get_code_files(repo_path)
        print(f"Found {len(code_chunks)} code chunks")
        
        # Run static analysis
        print("Running static analysis...")
        radon_result, pylint_score, complexity_issues = run_static_analysis(repo_path)
        
        # Run plagiarism check
        print("Running plagiarism check...")
        plagiarism_percent = run_plagiarism_check(repo_path)
        
        # Analyze repository structure
        print("Analyzing repository structure...")
        structure_analysis = analyze_repo_structure(repo_path)
        structure_score = sum([
            20 if structure_analysis["has_readme"] else 0,
            20 if structure_analysis["has_requirements"] else 0,
            15 if structure_analysis["has_tests"] else 0,
            15 if structure_analysis["has_dockerfile"] else 0,
            10 if structure_analysis["has_github_actions"] else 0,
            min(structure_analysis["file_count"] / 10, 20)  # Bonus for more files
        ])
        
        # Run LLM evaluation
        print("Running LLM evaluation...")
        logic, relevance, style, llm_feedback = evaluate_with_llm(project_desc, code_chunks)
        
        # Compute final score
        final_score = compute_final_score(
            plagiarism_percent, logic, relevance, style, pylint_score, structure_score
        )
        
        # Generate comprehensive feedback
        results = {
            "plagiarism_percent": plagiarism_percent,
            "logic": logic,
            "relevance": relevance,
            "style": style,
            "pylint_score": pylint_score,
            "radon_result": radon_result,
            "complexity_issues": complexity_issues,
            "final_score": final_score,
            "code_chunks_count": len(code_chunks),
            "structure_analysis": structure_analysis,
            "structure_score": structure_score,
            "llm_feedback": llm_feedback
        }
        
        feedback = generate_feedback(results)
        results["feedback"] = feedback
        
        return results
    finally:
        # Clean up with retry logic for permission issues
        max_retries = 3
        for retry in range(max_retries):
            try:
                if os.path.exists(repo_path):
                    # Force remove read-only files on Windows
                    def remove_readonly(func, path, excinfo):
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    
                    shutil.rmtree(repo_path, onerror=remove_readonly)
                    print(f"Successfully cleaned up {repo_path}")
                    break
            except PermissionError:
                if retry < max_retries - 1:
                    print(f"Permission error deleting {repo_path}, retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    print(f"Warning: Could not delete {repo_path} after {max_retries} attempts")

# ==========================================
# 🔟 Run Pipeline
# ==========================================
# if __name__ == "__main__":
#     github_url = "https://github.com/angermaster11/AI_HELPDESK.git"
#     project_desc = "AI-based Hackathon Project Evaluator System"
    
#     result = evaluate_repository(github_url, project_desc)
#     print(json.dumps(result, indent=4, default=str))

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from config.mongo import db
import asyncio

router = APIRouter()
collection = db["github_evaluations"]

@router.post("/evaluate")
async def evaluate_endpoint(req: Request):
    data = await req.json()
    github_url = data.get("github_url")
    project_desc = data.get("project_desc")
    hack_id = data.get("hack_id")
    team_id = data.get("team_id")
    team_code = data.get("team_code")

    if not github_url:
        raise HTTPException(status_code=400, detail="github_url is required")

    # Run evaluate_repository in thread pool if it's blocking
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, evaluate_repository, github_url, project_desc)

    if not result:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Optionally, save result in MongoDB
    collection.insert_one({
        "github_url": github_url,
        "project_desc": project_desc,
        "result": result,
        "hack_id" : hack_id,
        "team_id" : team_id,
        "team_code" : team_code
    })

    return JSONResponse(content=result)

@router.post("/getRound")
async def get_round(req: Request):
    data = await req.json()
    hack_id = data.get("hack_id")
    team_id = data.get("team_id")
    url = await db['submissions'].find_one({"hack_id": hack_id, "team_id": team_id,"round_index" : 1})
    url = url.get("submissions", {}).get("url", "")
    if url :
        return url
    else:
        return ""
