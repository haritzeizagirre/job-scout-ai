from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

from main import run_job_scout

app = FastAPI()

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scout_status = {
    "is_running": False,
    "matches_found": 0,
    "message": ""
}

class SaveCvRequest(BaseModel):
    cv_text: str

class RunScoutRequest(BaseModel):
    target_role: str
    boards: list[str]
    experience_level: str = "Any"
    additional_filters: str = ""

@app.get("/api/config")
def get_config():
    my_cv = ""
    if os.path.exists("my_cv.txt"):
        with open("my_cv.txt", "r", encoding="utf-8") as f:
            my_cv = f.read()
            
    boards = []
    if os.path.exists("boards.txt"):
        with open("boards.txt", "r", encoding="utf-8") as f:
            boards = [line.strip() for line in f if line.strip()]
            
    return {"my_cv": my_cv, "boards": boards}

@app.post("/api/save-cv")
def save_cv(req: SaveCvRequest):
    with open("my_cv.txt", "w", encoding="utf-8") as f:
        f.write(req.cv_text)
    return {"status": "success"}

def run_scout_task_wrapper(target_role: str, boards: list[str], my_cv: str, experience_level: str = "Any", additional_filters: str = ""):
    global scout_status
    scout_status["is_running"] = True
    scout_status["matches_found"] = 0
    scout_status["message"] = "Scouting in progress..."
    try:
        matches = run_job_scout(target_role, boards, my_cv, experience_level, additional_filters)
        scout_status["matches_found"] = matches or 0
        scout_status["message"] = "Finished successfully."
    except Exception as e:
        scout_status["message"] = f"Error: {str(e)}"
    finally:
        scout_status["is_running"] = False

@app.post("/api/run-scout")
def run_scout(req: RunScoutRequest, background_tasks: BackgroundTasks):
    global scout_status
    if scout_status["is_running"]:
        return {"status": "error", "message": "Scouting is already running!"}
        
    my_cv = ""
    if os.path.exists("my_cv.txt"):
        with open("my_cv.txt", "r", encoding="utf-8") as f:
            my_cv = f.read()
            
    # Run the scraping task in the background so the UI doesn't freeze
    background_tasks.add_task(run_scout_task_wrapper, req.target_role, req.boards, my_cv, req.experience_level, req.additional_filters)
    return {"status": "started", "message": "Scouting started in the background. Check your terminal for progress!"}

@app.get("/api/status")
def get_status():
    global scout_status
    return scout_status

@app.get("/api/outputs")
def get_outputs():
    outputs = []
    if os.path.exists("outputs"):
        for filename in os.listdir("outputs"):
            if filename.endswith(".md"):
                with open(os.path.join("outputs", filename), "r", encoding="utf-8") as f:
                    content = f.read()
                # Try to extract the title from the first line
                title = filename.replace(".md", "").replace("-", " ").title()
                first_line = content.split("\n")[0]
                if first_line.startswith("# "):
                    title = first_line[2:]
                
                # Strip "Cover Letter for " from title
                if title.lower().startswith("cover letter for "):
                    title = title[17:]
                
                outputs.append({"filename": filename, "title": title, "content": content})
    return {"outputs": outputs}

@app.get("/api/example-cv")
def get_example_cv():
    cv_text = ""
    if os.path.exists("example_cv.txt"):
        with open("example_cv.txt", "r", encoding="utf-8") as f:
            cv_text = f.read()
    return {"example_cv": cv_text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
