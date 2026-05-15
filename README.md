# Job Scout AI by Haritz Eizagirre

An automated, AI-powered job hunting agent that searches job boards on your behalf, evaluates each posting against your CV, and drafts a personalised cover letter for every role that's a genuine match.

Built with **LangGraph**, **Playwright**, **FastAPI**, and a vanilla HTML/JS frontend.

---

## What is this?

Job Scout AI is a personal assistant for your job search. Instead of manually browsing job boards one by one, you tell it what role you're looking for, paste in your CV, and let it do the rest.

It autonomously opens job boards in a headless browser, finds relevant postings, reads each one, and runs them through an AI evaluator that acts as a strict technical recruiter. Only jobs that genuinely match your profile make it through. For every match, a tailored cover letter is automatically drafted and saved.

Rejected jobs are remembered, so future runs never waste time re-evaluating the same listings.

---

## How it works

The scouting pipeline runs in five stages:

```
Job Boards  ──►  Navigator  ──►  Scraper  ──►  AI Evaluator  ──►  Cover Letter Drafter
(boards.txt)     (Playwright)    (adapter)      (LangGraph)         (LangGraph)
```

1. **Navigator** — Playwright opens each job board and an LLM agent searches for your target role by interacting with the page (search bars, filters, etc.), then extracts all job listing URLs from the results page.

2. **Scraper + Adapters** — Each job URL is visited. Specialised adapters (for JustRemote, NoDesk, WorkingNomads) use fast CSS selectors to extract the job title, company, and description. An AI-powered generic adapter handles any other site by reading raw page text.

3. **AI Evaluator** — A LangGraph node sends the job details and your CV to `gpt-4o-mini`. The prompt enforces strict rules: if the role title or description doesn't match your target role, if the experience level conflicts, or if any of your custom filters are violated, the job is immediately rejected. Only genuinely fitting roles pass.

4. **Cover Letter Drafter** — For every match, a second LangGraph node generates a professional 3-paragraph cover letter tailored to the specific job and company.

5. **Skip List** — Rejected URLs are saved to the database (or tracked in-memory for guests). On future runs they are skipped instantly, saving time and API cost.

Results are surfaced through a web dashboard and also written to the `outputs/` folder as Markdown files.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Workflow | LangGraph + LangChain + OpenAI / OpenRouter |
| Web Scraping | Playwright (headless Chromium) |
| Backend API | FastAPI + Uvicorn |
| Database | TursoDB (libSQL, cloud HTTP) |
| Auth | JWT (`python-jose`) + bcrypt (`passlib`) |
| Frontend | Vanilla HTML / CSS / JavaScript |

---

## Local Setup

### Prerequisites

- Python 3.10+
- An [OpenRouter](https://openrouter.ai) API key (or a direct OpenAI key)
- A free [Turso](https://turso.tech) database

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/haritzeizagirre/job-scout-ai.git
cd job-scout-ai

python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install the Playwright browser

```bash
playwright install chromium
```

### 4. Configure environment variables

Copy the template and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set:

```env
# Your OpenRouter (or OpenAI) key
OPENROUTER_API_KEY=sk-or-v1-...
OPENAI_API_KEY=${OPENROUTER_API_KEY}
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Turso database
TURSO_DATABASE_URL=https://your-db.turso.io
TURSO_AUTH_TOKEN=your-token

# A strong random secret for JWT tokens
# Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=your-secret-here

# Emails that become admins automatically on first registration
ADMIN_EMAILS=you@example.com

# ── Email verification (Gmail SMTP) ─────────────────────────────
# 1. Enable 2-Step Verification on your Google account
# 2. Generate an App Password at: https://myaccount.google.com/apppasswords
# 3. Use that App Password as SMTP_PASS (NOT your regular Gmail password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your-gmail-app-password
EMAIL_FROM=Job Scout AI <your@gmail.com>

# ── Base URL for verification links ─────────────────────────────
APP_BASE_URL=http://localhost:8000
```

### 5. Add the job boards you want to scan

Edit `boards.txt` — one URL per line:

```
https://justremote.co
https://nodesk.co
https://workingnomads.com/jobs
```

### 6. Start the backend API

```bash
uvicorn api:app --reload --port 8000
```

The API is now running at `http://localhost:8000`.

### 7. Open the frontend

Open `frontend/index.html` directly in your browser. That's it — no build step needed.

> **Tip:** If you prefer serving it with a local server (to avoid any browser CORS restrictions):
> ```bash
> python -m http.server 3000 --directory frontend
> ```
> Then visit `http://localhost:3000`.

---

## Using the Web Dashboard

1. **Register** — Click the login icon (top-right), enter your details, and click *Create Account*.
2. **Verify your email** — Check your inbox for the activation link. Click it to log in automatically.
3. **Paste your CV** — Go to the *Dashboard* tab, paste your CV text, and click *Save CV*.
3. **Configure your search** — Set your target role (e.g. `Backend Engineer`), experience level, and any extra filters (e.g. `Remote only, no startups`).
4. **Select boards** — Tick the job boards from `boards.txt` that you want to scan.
5. **Start Scouting** — Click the button. The agent runs in the background; status updates every few seconds.
6. **View Matches** — Switch to the *Matches* tab. Each card shows the job title, company, why it matched, and the generated cover letter.
7. **View Rejected Jobs** — Click *Show Rejected* to see non-matches and the AI's rejection reason.
8. **View History** — The *History* tab shows all past scouting runs with match and skip counts.

---

## Running the CLI (no frontend needed)

For a quick local test without the web UI:

```bash
python main.py
```

It reads `my_cv.txt` and `boards.txt`, lets you select which board to scan, and saves any matches as Markdown files inside `outputs/`.

To set the target role via environment variable:

```bash
TARGET_ROLE="Data Engineer" python main.py
```

---

## Promoting a user to Admin (unlimited runs)

After a user has registered through the web app, run:

```bash
python scripts/set_admin.py their@email.com
```

Admins bypass the monthly usage limits. You can also pre-configure `ADMIN_EMAILS` in `.env` to auto-promote specific addresses on registration.

---

## Usage Limits

| Tier | Scout Runs / Month | Tracking |
|---|---|---|
| Guest (no account) | 1 | By IP address |
| Free (registered) | 5 | By user in database |
| Admin | Unlimited | No limit applied |

---

## Project Structure

```
job-scout-ai/
├── api.py                  # FastAPI app — all HTTP routes
├── main.py                 # CLI entry point + core scouting logic
├── src/
│   ├── agents.py           # LLM agents: Evaluator + Cover Letter Drafter
│   ├── graph.py            # LangGraph workflow definition
│   ├── scraper.py          # Job page scraper + adapter selection
│   ├── navigator.py        # LLM-powered board navigator (Playwright)
│   ├── db.py               # TursoDB client + all query helpers
│   ├── auth.py             # JWT + bcrypt auth utilities
│   ├── email_sender.py     # SMTP verification email logic
│   ├── limits.py           # Rate limiting (guest / free / admin)
│   └── adapters/           # Board-specific CSS extractors
├── frontend/
│   ├── index.html          # Single Page App shell
│   ├── main.js             # Auth, API calls, UI logic
│   └── style.css           # Styles
├── scripts/
│   └── set_admin.py        # CLI: promote user to admin
├── boards.txt              # Job board URLs to scan
├── my_cv.txt               # Your CV (used by the CLI)
├── .env.example            # Environment variable template
└── requirements.txt        # Python dependencies
```