"""
Job Scout AI — FastAPI backend.
Handles auth, rate limiting, DB persistence, and background scouting.
"""
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import os

from src.db import (
    init_db,
    create_user,
    get_user_by_email,
    get_user_usage,
    get_guest_usage,
    increment_user_usage,
    increment_guest_usage,
    get_user_runs,
    get_user_matches,
    get_user_non_matches,
    save_cv,
    get_active_cv,
)
from src.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_auth,
    require_admin,
)
from src.limits import check_scout_limit, _get_client_ip
from main import run_job_scout

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Job Scout AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialise DB schema on startup
@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------------
# In-memory scout status (per-process, sufficient for single instance)
# ---------------------------------------------------------------------------

scout_status = {
    "is_running": False,
    "matches_found": 0,
    "skipped": 0,
    "message": "",
}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SaveCvRequest(BaseModel):
    cv_text: str

class RunScoutRequest(BaseModel):
    target_role: str
    boards: list[str]
    experience_level: str = "Any"
    additional_filters: str = ""


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.post("/api/auth/register")
def register(req: RegisterRequest):
    if get_user_by_email(req.email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    hashed = hash_password(req.password)
    user = create_user(req.email, hashed)
    token = create_access_token(user["id"])
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "role": user["role"]}}


@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_access_token(user["id"])
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "role": user["role"]}}


@app.get("/api/auth/me")
def me(user: dict = Depends(require_auth)):
    usage = get_user_usage(user["id"])
    return {
        "user": {"id": user["id"], "email": user["email"], "role": user["role"]},
        "usage": usage,
    }


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

class SetRoleRequest(BaseModel):
    email: EmailStr
    role: str  # 'free' | 'admin'

@app.post("/api/admin/set-role")
def admin_set_role(req: SetRoleRequest, admin: dict = Depends(require_admin)):
    from src.db import set_user_role
    if req.role not in ("free", "admin"):
        raise HTTPException(status_code=400, detail="Role must be 'free' or 'admin'.")
    target = get_user_by_email(req.email)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    set_user_role(req.email, req.role)
    return {"status": "ok", "email": req.email, "role": req.role}


# ---------------------------------------------------------------------------
# Config / CV routes
# ---------------------------------------------------------------------------

@app.get("/api/config")
def get_config(user: dict | None = Depends(get_current_user)):
    my_cv = ""

    if user:
        # Authenticated user: load from DB
        my_cv = get_active_cv(user["id"]) or ""
    else:
        # Guest fallback: load from file
        if os.path.exists("my_cv.txt"):
            with open("my_cv.txt", "r", encoding="utf-8") as f:
                my_cv = f.read()

    boards = []
    if os.path.exists("boards.txt"):
        with open("boards.txt", "r", encoding="utf-8") as f:
            boards = [line.strip() for line in f if line.strip()]

    return {"my_cv": my_cv, "boards": boards}


@app.post("/api/save-cv")
def save_cv_endpoint(req: SaveCvRequest, user: dict | None = Depends(get_current_user)):
    if user:
        save_cv(user["id"], req.cv_text)
    else:
        # Guest: save to file as before
        with open("my_cv.txt", "w", encoding="utf-8") as f:
            f.write(req.cv_text)
    return {"status": "success"}


@app.get("/api/example-cv")
def get_example_cv():
    cv_text = ""
    if os.path.exists("example_cv.txt"):
        with open("example_cv.txt", "r", encoding="utf-8") as f:
            cv_text = f.read()
    return {"example_cv": cv_text}


# ---------------------------------------------------------------------------
# Scout routes
# ---------------------------------------------------------------------------

def _run_scout_background(
    run_id: str,
    user_id: str | None,
    guest_ip: str | None,
    target_role: str,
    boards: list[str],
    my_cv: str,
    experience_level: str,
    additional_filters: str,
):
    global scout_status
    scout_status["is_running"] = True
    scout_status["matches_found"] = 0
    scout_status["skipped"] = 0
    scout_status["message"] = "Scouting in progress..."

    try:
        result = run_job_scout(
            target_role=target_role,
            boards=boards,
            my_cv=my_cv,
            experience_level=experience_level,
            additional_filters=additional_filters,
            run_id=run_id,
            user_id=user_id,
        )
        scout_status["matches_found"] = result.get("matches", 0)
        scout_status["skipped"] = result.get("skipped", 0)
        scout_status["message"] = "Finished successfully."

        # Increment usage counters
        if user_id:
            increment_user_usage(user_id, scout_runs=1, ai_calls=result.get("ai_calls", 0))
        elif guest_ip:
            increment_guest_usage(guest_ip)

    except Exception as e:
        scout_status["message"] = f"Error: {str(e)}"
    finally:
        scout_status["is_running"] = False


@app.post("/api/run-scout")
def run_scout(
    req: RunScoutRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: dict | None = Depends(get_current_user),
):
    global scout_status
    if scout_status["is_running"]:
        return {"status": "error", "message": "A scout run is already in progress!"}

    # Check rate limits
    check_scout_limit(request, user)

    guest_ip = None if user else _get_client_ip(request)

    # Get CV
    my_cv = ""
    if user:
        my_cv = get_active_cv(user["id"]) or ""
    elif os.path.exists("my_cv.txt"):
        with open("my_cv.txt", "r", encoding="utf-8") as f:
            my_cv = f.read()

    if not my_cv.strip():
        return {"status": "error", "message": "Please save your CV before scouting."}

    # Create a run record
    from src.db import create_scout_run
    run_id = create_scout_run(
        user_id=user["id"] if user else None,
        guest_ip=guest_ip,
        target_role=req.target_role,
        boards=req.boards,
        experience=req.experience_level,
        filters=req.additional_filters,
    )

    background_tasks.add_task(
        _run_scout_background,
        run_id=run_id,
        user_id=user["id"] if user else None,
        guest_ip=guest_ip,
        target_role=req.target_role,
        boards=req.boards,
        my_cv=my_cv,
        experience_level=req.experience_level,
        additional_filters=req.additional_filters,
    )

    return {"status": "started", "run_id": run_id, "message": "Scouting started in the background."}


@app.get("/api/status")
def get_status():
    return scout_status


# ---------------------------------------------------------------------------
# History routes (authenticated)
# ---------------------------------------------------------------------------

@app.get("/api/history/runs")
def history_runs(user: dict = Depends(require_auth)):
    return {"runs": get_user_runs(user["id"])}


@app.get("/api/history/matches")
def history_matches(user: dict = Depends(require_auth)):
    return {"matches": get_user_matches(user["id"])}


@app.get("/api/history/non-matches")
def history_non_matches(user: dict = Depends(require_auth)):
    return {"non_matches": get_user_non_matches(user["id"])}



# ---------------------------------------------------------------------------
# Legacy outputs endpoint (reads from filesystem — kept for backwards compat)
# ---------------------------------------------------------------------------

@app.get("/api/outputs")
def get_outputs(user: dict | None = Depends(get_current_user)):
    # Guests have no persistent matches — return empty so they don't see
    # another user's files from the outputs/ folder.
    if not user:
        return {"outputs": []}

    # Authenticated users: serve from DB
    matches = get_user_matches(user["id"])
    outputs = []
    for m in matches:
        title = f"{m['job_title']} at {m['company']}" if m.get("job_title") else "Unknown Job"
        content = (
            f"# {title}\n\n"
            f"**URL:** {m.get('job_url', '')}\n\n"
            f"**Reason for Match:** {m.get('match_reason', '')}\n\n"
            "---\n\n"
            f"{m.get('cover_letter', '')}"
        )
        outputs.append({"filename": m["id"] + ".md", "title": title, "content": content})
    return {"outputs": outputs}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# ── Serve frontend (must be LAST — after all /api/ routes) ──────────────────
# Works for both local dev (localhost:8000) and production (behind Nginx)
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
