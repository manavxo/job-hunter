# Job Hunter — Anti-Gravity IDE Instructions

## Project
Automated job application web app. Scrapes PM jobs daily, customizes resume + cover letter via LLM, finds hiring manager contacts, sends personalized emails. Runs on a server — no local dependencies.

## Architecture
```
frontend/          → Static HTML/CSS/JS dashboard (Vercel or served by backend)
backend/
  main.py          → FastAPI server + APScheduler + all API routes
  database.py      → SQLite (settings, jobs, applications)
  pipeline/
    scrape.py      → Job scraping via jobspy
    contacts.py    → Free contact finder (web search + SMTP verify)
    customize.py   → LLM resume + cover letter tailoring
    send.py        → Gmail SMTP email sending
```

## Run Locally
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Open http://localhost:8000
```

## Deploy
- **Backend**: Railway (free tier) — push `backend/` folder
- **Frontend**: Served by backend at `/app` or deploy separately to Vercel
- After deploy, update `API` constant in `frontend/index.html` to your Railway URL

## API Endpoints
| Method | Path | What it does |
|---|---|---|
| GET | `/api/settings` | Get all settings |
| PUT | `/api/settings` | Update settings |
| GET | `/api/jobs` | List scraped jobs |
| GET | `/api/jobs/new` | List new (unapplied) jobs |
| GET | `/api/applications` | List application history |
| GET | `/api/applications/stats` | Dashboard stats |
| POST | `/api/pipeline/run` | Run full pipeline |
| POST | `/api/pipeline/scrape` | Just scrape jobs |
| GET | `/api/schedule` | Get schedule info |
| PUT | `/api/schedule` | Update schedule time |
| GET | `/api/health` | Health check |

## Daily Flow (what happens at 8:00 AM)
1. Scrapes LinkedIn, Indeed, Glassdoor, Google for PM jobs (last 24h)
2. Scores and selects top 10 by relevance
3. For each: finds contact via web search + SMTP verification (free, no API key)
4. Customizes resume + cover letter via LLM
5. Sends personalized email via Gmail SMTP
6. Logs everything to SQLite

## Config (all via web dashboard — Settings tab)
- Candidate profile (name, email, phone, LinkedIn)
- Job search (titles, locations, salary, jobs per day)
- LLM (API base URL, key, model)
- Email (Gmail address + App Password)
- Resume + cover letter templates

## Frontend Design
READ `FRONTEND-DESIGN.md` before touching any HTML. It contains:
- Complete color palette (CSS custom properties)
- Typography scale (Inter, weights, sizes, spacing)
- Every component spec (cards, buttons, inputs, tables, badges, tabs)
- Layout structure and grid rules
- Anti-slop rules (what NOT to do)
- Responsive breakpoints
- API integration reference
- Verification checklist

The design is Linear-inspired dark mode: near-black backgrounds, semi-transparent borders, ONE accent color, no gradients, no glassmorphism, no emoji.

## Tech Stack
- **Backend**: Python 3.11, FastAPI, APScheduler, SQLite
- **Scraping**: python-jobspy
- **Contact finding**: DuckDuckGo search + DNS MX + SMTP verification
- **LLM**: Any OpenAI-compatible API (OpenRouter, OpenAI, etc.)
- **Email**: Gmail SMTP
- **Frontend**: Vanilla HTML/CSS/JS (no build step). Google Fonts: Inter only.

## Files to modify when extending
- Add new job board → `pipeline/scrape.py` (add to `site_name` list)
- Change scoring → `pipeline/scrape.py` → `score_job()`
- Change email template → `pipeline/send.py` → `compose_email()`
- Add new API route → `main.py`
- Change UI → `frontend/index.html`
