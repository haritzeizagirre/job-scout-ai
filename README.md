# Job Scout AI

**Student:** Haritz Eizagirre

An automated, multi-user AI assistant that streamlines the job search process. It autonomously navigates job boards, evaluates postings against your personal CV using an LLM, drafts tailored cover letters for matches, and remembers rejected jobs so they are never re-analysed in future runs.

Built with **LangGraph**, **Playwright**, **FastAPI**, **TursoDB**, and a vanilla HTML/JS frontend served via **Nginx on AWS EC2**.

---

## Features

- **Autonomous Job Board Navigator** — Navigates supported job boards (JustRemote, NoDesk, Working Nomads, etc.), searches for your target role using an LLM-powered agent, and extracts relevant job links.
- **Smart Adapter Pattern** — Selects the best extraction strategy per URL:
  - *JustRemote / NoDesk / WorkingNomads Adapters* — Fast CSS-selector-based extraction.
  - *Generic AI Adapter* — Fallback that uses OpenAI to structure job title, company and description from raw page text.
- **AI Evaluator** — Strict technical recruiter agent that compares job requirements to your CV and decides if you are a match (with a written reason).
- **AI Cover Letter Drafter** — Automatically writes a professional, 3-paragraph cover letter for every match.
- **Non-match Skip List** — Rejected job URLs are stored per user. Future runs skip them instantly, saving time and AI cost.
- **User Accounts & JWT Auth** — Register/login with email + password. Tokens stored client-side, all API calls are authenticated.
- **Usage Limits by Tier** — Guests (1 scout run/month, IP-tracked), Free accounts (5 runs/month), Admin accounts (unlimited).
- **Persistent History** — All scout runs, matches, and non-matches are saved to TursoDB and viewable in the dashboard.
- **Admin Role** — Promote any user to admin via CLI (`scripts/set_admin.py`). Admins bypass all limits.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Workflow | LangGraph + LangChain + OpenAI (via OpenRouter) |
| Web Scraping | Playwright (headless Chromium) |
| Backend API | FastAPI + Uvicorn |
| Database | TursoDB (libSQL, cloud HTTP) |
| Auth | JWT (`python-jose`) + bcrypt (`passlib`) |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Reverse Proxy | Nginx |
| Hosting | AWS EC2 (Ubuntu) |

---

## Prerequisites

- Python 3.10+
- An OpenAI or OpenRouter API key
- A [Turso](https://turso.tech) account (free tier is sufficient) with a database created

---

## Local Setup

1. **Clone the repository and create a virtual environment:**
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright's Chromium browser:**
   ```bash
   playwright install chromium
   ```

4. **Configure environment variables:**
   Copy `.env.example` to `.env` and fill in your values:
   ```env
   OPENROUTER_API_KEY="your_key_here"
   OPENAI_API_KEY="${OPENROUTER_API_KEY}"
   OPENAI_BASE_URL="https://openrouter.ai/api/v1"

   TURSO_DATABASE_URL="libsql://your-db.turso.io"
   TURSO_AUTH_TOKEN="your-turso-token"

   # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
   JWT_SECRET_KEY="your-strong-random-secret"

   # Auto-promote these emails to admin on first register (comma-separated)
   ADMIN_EMAILS=teacher@example.com
   ```

5. **Add your job boards:**
   Edit `boards.txt` — one URL per line:
   ```
   https://justremote.co
   https://nodesk.co
   https://workingnomads.com/jobs
   ```

6. **Run the API server:**
   ```bash
   uvicorn api:app --reload --port 8000
   ```

7. **Open the frontend:**
   Open `frontend/index.html` in a browser, or serve it with any static server. The JS uses relative `/api/` paths, which work seamlessly behind Nginx.

---

## How to Use (Web UI)

1. **Register** an account via the login modal (top-right of the header).
2. **Paste your CV** in the Dashboard and click *Save CV*.
3. **Configure** your target role, experience level, optional filters, and select the boards to scan.
4. **Click *Start Scouting*** — the agent runs in the background (headless browser).
5. **Monitor progress** — the status message updates every 3 seconds.
6. **View Matches** — switch to the *Matches* tab to see matching jobs and open their cover letters.
7. **View Rejected Jobs** — click *Show Rejected* to see non-matches with the AI's rejection reasons. These URLs are skip-listed for all your future runs.
8. **View History** — the *History* tab (logged-in users only) shows all past scout runs with match and skip counts.

---

## Promoting a User to Admin (Unlimited Access)

After the user has registered via the web app, run this once on the server:

```bash
python scripts/set_admin.py teacher@example.com
```

The user is immediately promoted. Admin accounts have no monthly limits.

> **Tip:** You can also pre-configure `ADMIN_EMAILS=teacher@example.com` in `.env` so they are auto-promoted the moment they register.

---

## AWS EC2 + Nginx Deployment

### 1. Install system dependencies on the EC2 instance

```bash
sudo apt update && sudo apt install -y nginx python3-pip python3-venv
```

### 2. Copy the project and install Python deps

```bash
sudo mkdir -p /var/www/job-scout-ai
sudo cp -r . /var/www/job-scout-ai/
cd /var/www/job-scout-ai
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/playwright install chromium
./venv/bin/playwright install-deps
```

### 3. Configure Nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/jobscout
sudo ln -s /etc/nginx/sites-available/jobscout /etc/nginx/sites-enabled/
# Edit the file and replace your-domain.com with your actual domain
sudo nano /etc/nginx/sites-available/jobscout
sudo nginx -t && sudo systemctl reload nginx
```

### 4. Install and start the systemd service

```bash
sudo cp deploy/jobscout.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable jobscout
sudo systemctl start jobscout
sudo systemctl status jobscout
```

### 5. Enable HTTPS (optional but recommended)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```
Then uncomment the HTTPS block in `deploy/nginx.conf`.

---

## Project Structure

```
job-scout-ai/
├── api.py                  # FastAPI app — all HTTP routes
├── main.py                 # Core scouting logic (Playwright + LangGraph)
├── src/
│   ├── agents.py           # LLM agents: Evaluator + Cover Letter Drafter
│   ├── graph.py            # LangGraph workflow definition
│   ├── scraper.py          # Job page scraper + adapter selection
│   ├── navigator.py        # LLM-powered board navigator
│   ├── db.py               # TursoDB client + all query helpers
│   ├── auth.py             # JWT + bcrypt auth utilities
│   ├── limits.py           # Rate limiting (guest / free / admin)
│   └── adapters/           # Board-specific CSS extractors
├── frontend/
│   ├── index.html          # Single Page App shell
│   ├── main.js             # Auth, API calls, UI logic
│   └── style.css           # Styles
├── scripts/
│   └── set_admin.py        # CLI: promote user to admin
├── deploy/
│   ├── nginx.conf          # Nginx reverse proxy config
│   └── jobscout.service    # systemd service definition
├── boards.txt              # Job board URLs to scan
├── .env.example            # Environment variable template
└── requirements.txt        # Python dependencies
```

---

## Usage Limits

| Tier | Scout Runs / Month | How tracked |
|---|---|---|
| Guest (no account) | 1 | By IP address |
| Free (registered) | 5 | By user in database |
| Admin | Unlimited | Bypasses all checks |