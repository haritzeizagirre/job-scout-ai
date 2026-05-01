"""
TursoDB client and all query helpers for Job Scout AI.
Uses libsql-client (HTTP driver, works with Turso cloud).
"""
import os
import uuid
import json
from datetime import datetime
from typing import Optional

import libsql_client

_client: Optional[libsql_client.Client] = None


def get_client() -> libsql_client.Client:
    global _client
    if _client is None:
        url = os.environ.get("TURSO_DATABASE_URL")
        token = os.environ.get("TURSO_AUTH_TOKEN")
        if not url or not token:
            raise RuntimeError("TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be set in .env")
        _client = libsql_client.create_client_sync(url=url, auth_token=token)
    return _client


def _now_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


# ---------------------------------------------------------------------------
# Schema initialisation — call once at startup
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'free',
    created_at    INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS usage (
    user_id    TEXT NOT NULL,
    month      TEXT NOT NULL,
    scout_runs INTEGER NOT NULL DEFAULT 0,
    ai_calls   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, month)
);

CREATE TABLE IF NOT EXISTS guest_usage (
    ip         TEXT NOT NULL,
    month      TEXT NOT NULL,
    scout_runs INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (ip, month)
);

CREATE TABLE IF NOT EXISTS scout_runs (
    id          TEXT PRIMARY KEY,
    user_id     TEXT,
    guest_ip    TEXT,
    target_role TEXT NOT NULL,
    boards      TEXT NOT NULL,
    experience  TEXT,
    filters     TEXT,
    started_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    status      TEXT NOT NULL DEFAULT 'running',
    match_count INTEGER NOT NULL DEFAULT 0,
    skip_count  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS matches (
    id           TEXT PRIMARY KEY,
    run_id       TEXT NOT NULL,
    user_id      TEXT,
    job_title    TEXT,
    company      TEXT,
    job_url      TEXT,
    match_reason TEXT,
    cover_letter TEXT,
    created_at   INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS non_matches (
    id               TEXT PRIMARY KEY,
    run_id           TEXT NOT NULL,
    user_id          TEXT,
    job_url          TEXT NOT NULL,
    job_title        TEXT,
    company          TEXT,
    rejection_reason TEXT,
    created_at       INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_non_matches_user_url
    ON non_matches (user_id, job_url);

CREATE TABLE IF NOT EXISTS cvs (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    label      TEXT NOT NULL DEFAULT 'Default',
    content    TEXT NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);
"""


def init_db():
    """Run schema creation. Safe to call multiple times (uses IF NOT EXISTS)."""
    client = get_client()
    for statement in SCHEMA_SQL.strip().split(";"):
        stmt = statement.strip()
        if stmt:
            client.execute(stmt)


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def create_user(email: str, password_hash: str) -> dict:
    user_id = str(uuid.uuid4())
    client = get_client()

    # Auto-promote admin emails from env
    admin_emails = [e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()]
    role = "admin" if email.lower() in admin_emails else "free"

    client.execute(
        "INSERT INTO users (id, email, password_hash, role) VALUES (?, ?, ?, ?)",
        [user_id, email, password_hash, role],
    )
    return {"id": user_id, "email": email, "role": role}


def get_user_by_email(email: str) -> Optional[dict]:
    client = get_client()
    rs = client.execute("SELECT id, email, password_hash, role FROM users WHERE email = ?", [email])
    if rs.rows:
        row = rs.rows[0]
        return {"id": row[0], "email": row[1], "password_hash": row[2], "role": row[3]}
    return None


def get_user_by_id(user_id: str) -> Optional[dict]:
    client = get_client()
    rs = client.execute("SELECT id, email, role FROM users WHERE id = ?", [user_id])
    if rs.rows:
        row = rs.rows[0]
        return {"id": row[0], "email": row[1], "role": row[2]}
    return None


def set_user_role(email: str, role: str):
    client = get_client()
    client.execute("UPDATE users SET role = ? WHERE email = ?", [role, email])


# ---------------------------------------------------------------------------
# Usage / rate-limit helpers
# ---------------------------------------------------------------------------

def get_user_usage(user_id: str) -> dict:
    client = get_client()
    month = _now_month()
    rs = client.execute(
        "SELECT scout_runs, ai_calls FROM usage WHERE user_id = ? AND month = ?",
        [user_id, month],
    )
    if rs.rows:
        return {"scout_runs": rs.rows[0][0], "ai_calls": rs.rows[0][1], "month": month}
    return {"scout_runs": 0, "ai_calls": 0, "month": month}


def increment_user_usage(user_id: str, scout_runs: int = 0, ai_calls: int = 0):
    client = get_client()
    month = _now_month()
    client.execute(
        """INSERT INTO usage (user_id, month, scout_runs, ai_calls)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, month)
           DO UPDATE SET
               scout_runs = scout_runs + excluded.scout_runs,
               ai_calls   = ai_calls   + excluded.ai_calls""",
        [user_id, month, scout_runs, ai_calls],
    )


def get_guest_usage(ip: str) -> dict:
    client = get_client()
    month = _now_month()
    rs = client.execute(
        "SELECT scout_runs FROM guest_usage WHERE ip = ? AND month = ?",
        [ip, month],
    )
    if rs.rows:
        return {"scout_runs": rs.rows[0][0], "month": month}
    return {"scout_runs": 0, "month": month}


def increment_guest_usage(ip: str):
    client = get_client()
    month = _now_month()
    client.execute(
        """INSERT INTO guest_usage (ip, month, scout_runs)
           VALUES (?, ?, 1)
           ON CONFLICT(ip, month)
           DO UPDATE SET scout_runs = scout_runs + 1""",
        [ip, month],
    )


# ---------------------------------------------------------------------------
# Scout run helpers
# ---------------------------------------------------------------------------

def create_scout_run(
    user_id: Optional[str],
    guest_ip: Optional[str],
    target_role: str,
    boards: list,
    experience: str = "",
    filters: str = "",
) -> str:
    run_id = str(uuid.uuid4())
    client = get_client()
    client.execute(
        """INSERT INTO scout_runs (id, user_id, guest_ip, target_role, boards, experience, filters)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [run_id, user_id, guest_ip, target_role, json.dumps(boards), experience, filters],
    )
    return run_id


def update_scout_run(run_id: str, status: str, match_count: int, skip_count: int):
    client = get_client()
    client.execute(
        "UPDATE scout_runs SET status = ?, match_count = ?, skip_count = ? WHERE id = ?",
        [status, match_count, skip_count, run_id],
    )


def get_user_runs(user_id: str) -> list:
    client = get_client()
    rs = client.execute(
        """SELECT id, target_role, boards, experience, started_at, status, match_count, skip_count
           FROM scout_runs WHERE user_id = ? ORDER BY started_at DESC LIMIT 50""",
        [user_id],
    )
    result = []
    for row in rs.rows:
        result.append({
            "id": row[0],
            "target_role": row[1],
            "boards": json.loads(row[2]) if row[2] else [],
            "experience": row[3],
            "started_at": row[4],
            "status": row[5],
            "match_count": row[6],
            "skip_count": row[7],
        })
    return result


# ---------------------------------------------------------------------------
# Non-match helpers (skip-list logic)
# ---------------------------------------------------------------------------

def is_url_already_rejected(user_id: str, job_url: str) -> bool:
    """Returns True if this user has already rejected this URL before."""
    client = get_client()
    rs = client.execute(
        "SELECT 1 FROM non_matches WHERE user_id = ? AND job_url = ?",
        [user_id, job_url],
    )
    return len(rs.rows) > 0


def save_non_match(
    run_id: str,
    user_id: Optional[str],
    job_url: str,
    job_title: str,
    company: str,
    rejection_reason: str,
):
    """Save a rejected job. Uses INSERT OR IGNORE so duplicates are safe."""
    if not user_id:
        return  # Don't persist guest non-matches
    client = get_client()
    client.execute(
        """INSERT OR IGNORE INTO non_matches
           (id, run_id, user_id, job_url, job_title, company, rejection_reason)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [str(uuid.uuid4()), run_id, user_id, job_url, job_title, company, rejection_reason],
    )


def get_user_non_matches(user_id: str, limit: int = 100) -> list:
    client = get_client()
    rs = client.execute(
        """SELECT id, job_url, job_title, company, rejection_reason, created_at
           FROM non_matches WHERE user_id = ?
           ORDER BY created_at DESC LIMIT ?""",
        [user_id, limit],
    )
    result = []
    for row in rs.rows:
        result.append({
            "id": row[0],
            "job_url": row[1],
            "job_title": row[2],
            "company": row[3],
            "rejection_reason": row[4],
            "created_at": row[5],
        })
    return result


# ---------------------------------------------------------------------------
# Match helpers
# ---------------------------------------------------------------------------

def save_match(
    run_id: str,
    user_id: Optional[str],
    job_url: str,
    job_title: str,
    company: str,
    match_reason: str,
    cover_letter: str,
):
    if not user_id:
        return  # Guests: results only shown in-session, not persisted
    client = get_client()
    client.execute(
        """INSERT INTO matches
           (id, run_id, user_id, job_url, job_title, company, match_reason, cover_letter)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [str(uuid.uuid4()), run_id, user_id, job_url, job_title, company, match_reason, cover_letter],
    )


def get_user_matches(user_id: str, limit: int = 100) -> list:
    client = get_client()
    rs = client.execute(
        """SELECT id, run_id, job_url, job_title, company, match_reason, cover_letter, created_at
           FROM matches WHERE user_id = ?
           ORDER BY created_at DESC LIMIT ?""",
        [user_id, limit],
    )
    result = []
    for row in rs.rows:
        result.append({
            "id": row[0],
            "run_id": row[1],
            "job_url": row[2],
            "job_title": row[3],
            "company": row[4],
            "match_reason": row[5],
            "cover_letter": row[6],
            "created_at": row[7],
        })
    return result


# ---------------------------------------------------------------------------
# CV helpers
# ---------------------------------------------------------------------------

def save_cv(user_id: str, content: str, label: str = "Default"):
    """Upsert the active CV for a user (replaces existing active one)."""
    client = get_client()
    # Deactivate old CVs
    client.execute("UPDATE cvs SET is_active = 0 WHERE user_id = ?", [user_id])
    # Insert new active
    client.execute(
        "INSERT INTO cvs (id, user_id, label, content, is_active) VALUES (?, ?, ?, ?, 1)",
        [str(uuid.uuid4()), user_id, label, content],
    )


def get_active_cv(user_id: str) -> Optional[str]:
    client = get_client()
    rs = client.execute(
        "SELECT content FROM cvs WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
        [user_id],
    )
    if rs.rows:
        return rs.rows[0][0]
    return None
