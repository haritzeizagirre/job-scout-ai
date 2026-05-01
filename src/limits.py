"""
Rate limiting for Job Scout AI.

Tiers:
  - guest  (no account): 1 scout run / month, tracked by IP
  - free   (registered): 5 scout runs / month, tracked by user_id in DB
  - admin              : unlimited
"""
from fastapi import HTTPException, Request, status

from src.db import get_user_usage, get_guest_usage

# Monthly limits per tier
LIMITS = {
    "guest": {"scout_runs": 1},
    "free":  {"scout_runs": 5},
    "admin": {"scout_runs": None},  # None = unlimited
}


def check_scout_limit(request: Request, user: dict | None):
    """
    Raises HTTP 429 if the user / guest has exceeded their monthly scout-run limit.
    Call this at the start of /api/run-scout before doing any work.
    """
    if user is None:
        # Guest path — use IP
        ip = _get_client_ip(request)
        usage = get_guest_usage(ip)
        limit = LIMITS["guest"]["scout_runs"]
        if usage["scout_runs"] >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Guest limit reached ({limit} scout run/month). "
                    "Please register for a free account to get more scans."
                ),
            )
        return

    role = user.get("role", "free")
    limit = LIMITS.get(role, LIMITS["free"])["scout_runs"]

    if limit is None:
        return  # Admin — unlimited

    usage = get_user_usage(user["id"])
    if usage["scout_runs"] >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Monthly limit reached ({limit} scout runs/month for '{role}' tier). "
                "Contact the admin if you need more."
            ),
        )


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Real-IP set by Nginx."""
    forwarded = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
