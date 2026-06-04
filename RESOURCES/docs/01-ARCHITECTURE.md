# Architecture

## System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Railway (free tier)                         │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  FastAPI Server (main.py)                               │ │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐ │ │
│  │  │ API Routes│  │Scheduler │  │ Static Files (/app)   │ │ │
│  │  └────┬─────┘  └────┬─────┘  └───────────────────────┘ │ │
│  │       │              │                                   │ │
│  │  ┌────▼──────────────▼───────────────────────────────┐  │ │
│  │  │           Pipeline Engine                          │  │ │
│  │  │  scrape → select → enrich → contacts → apply → log│  │ │
│  │  └────────────────────┬──────────────────────────────┘  │ │
│  │                       │                                  │ │
│  │  ┌────────────────────▼──────────────────────────────┐  │ │
│  │  │           SQLite (settings, jobs, applications)    │  │ │
│  │  └───────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  External: LinkedIn | Indeed | Craigslist | Glassdoor        │
│            OpenRouter (LLM) | Gmail SMTP                     │
└──────────────────────────────────────────────────────────────┘
```

## Database Schema

### `settings` — key-value config store
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL  -- JSON-encoded
);
```

Keys and their JSON shapes:
- `candidate` — `{name, email, phone, linkedin, location, title_target}`
- `search` — `{job_titles[], locations[], platforms[], region, jobs_per_day, hours_old, min_salary, distance_miles}`
- `llm` — `{api_base, api_key, model, max_tokens, temperature}`
- `platform_credentials` — `{linkedin: {email, password}, indeed: {email, password}, ...}`
- `email` — `{smtp_host, smtp_port, username, password, from_name, from_email, signature}`
- `resume_mode` — `"honest"` or `"enhanced"`
- `base_resume` — Full resume text (markdown)
- `base_cover_letter` — Cover letter template (markdown)
- `schedule_hour` — int (0-23)
- `schedule_minute` — int (0-59)

**Note:** `platform_credentials` stores login info for platforms the user already has accounts on. The user creates accounts himself. The system just logs in.

### `jobs` — scraped postings
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    description TEXT,
    job_url TEXT,
    date_posted TEXT,
    site TEXT,
    salary_min TEXT,
    salary_max TEXT,
    relevance_score REAL DEFAULT 0,
    status TEXT DEFAULT 'new',
    scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### `applications` — sent applications
```sql
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    title TEXT,
    company TEXT,
    contact_name TEXT,
    contact_email TEXT,
    contact_source TEXT,
    resume_text TEXT,
    cover_letter TEXT,
    resume_mode TEXT,
    apply_method TEXT,
    apply_status TEXT DEFAULT 'pending',
    outreach_status TEXT DEFAULT 'pending',
    error TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
```

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/settings` | Get all settings (secrets masked) |
| `PUT` | `/api/settings` | Update settings |
| `GET` | `/api/jobs?limit=50` | List scraped jobs |
| `GET` | `/api/applications?limit=100` | Application history |
| `GET` | `/api/applications/stats` | Dashboard stats |
| `GET` | `/api/platforms` | Available platforms |
| `POST` | `/api/pipeline/run` | Trigger pipeline |
| `POST` | `/api/pipeline/scrape` | Just scrape |
| `GET` | `/api/schedule` | Get schedule |
| `PUT` | `/api/schedule?hour=8&minute=0` | Update schedule |
| `GET` | `/api/health` | Health check |

## Key Design Decisions

1. **User creates accounts, system logs in.** No auto-signup. The friend makes LinkedIn, Indeed, etc. accounts himself. System stores credentials and reuses them via Playwright.
2. **Resume enrichment is its own module.** `pipeline/enrich.py` handles all LLM calls. Separated from apply/send logic.
3. **Dual apply channels.** Platform apply (browser) + email outreach both run per job.
4. **Craigslist is special.** No portal — extracts email/phone from post, sends directly.
5. **Region is configurable.** `search.region` maps to country codes for jobspy.
6. **10 style variants.** Each daily application gets a different resume angle + cover letter hook.
