# Job Hunter — Project Overview

## What This Is

A fully automated web application that applies to jobs every day. The user sets up accounts on job platforms himself, enters credentials once, and the system handles everything: scraping, customizing, applying, and outreach.

## The Daily Flow

```
8:00 AM — Scheduler triggers
    │
    ├─ 1. SCRAPE — LinkedIn, Indeed, Craigslist, Glassdoor, Google, ZipRecruiter
    │     → Filter: last 24h, user's target roles, user's locations, user's region
    │
    ├─ 2. SELECT — Score by relevance, dedupe, pick top 10
    │
    ├─ 3. ENRICH — For each job:
    │     → Analyze JD (skills, keywords, requirements)
    │     → Compare to user's resume (gaps, strengths)
    │     → Generate tailored resume (honest OR enhanced mode)
    │     → Generate tailored cover letter
    │     → Vary style so each application looks unique
    │
    ├─ 4. CONTACT — Find hiring manager email
    │     → Web search → email permutation → SMTP verify
    │
    ├─ 5. APPLY — Submit through the platform
    │     → LinkedIn/Indeed/Glassdoor: Playwright logs in with stored credentials
    │     → Craigslist: extract email/phone from post, send directly
    │     → External sites: browser form fill or email fallback
    │
    ├─ 6. OUTREACH — Email hiring manager directly (second channel)
    │
    └─ 7. LOG — Record everything, never re-apply
```

## What the User Does (One-Time Setup)

1. Create accounts on: LinkedIn, Indeed, Glassdoor, Craigslist (any platforms he wants)
2. Open the web dashboard
3. Fill in: name, email, phone, LinkedIn, location
4. Choose: target job titles, locations, platforms, region
5. Choose: resume mode (honest or enhanced)
6. Paste: his resume content and cover letter template
7. Enter: platform credentials (login email + password for each)
8. Enter: Gmail App Password (for sending emails)
9. Enter: OpenRouter API key (for LLM)
10. Hit save. Done.

## Resume Modes

| Mode | What It Does |
|---|---|
| **Honest** | Optimizes existing experience — reorders, mirrors keywords, strengthens language |
| **Enhanced** | Strategically adds relevant skills, fills gaps, embellishes — maximizes interview chances |

Both modes: ATS-optimized, context-driven (tailored to each JD), varied across the 10 daily applications.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI + APScheduler |
| Database | SQLite |
| Scraping | jobspy + custom Craigslist scraper |
| Contact finder | DuckDuckGo + DNS + SMTP (free, no API) |
| Enrichment | LLM (OpenRouter or any OpenAI-compatible) |
| Platform apply | Playwright (browser automation) |
| Email | Gmail SMTP |
| Frontend | Single HTML file (vanilla JS) |
| Hosting | Railway (free tier) |

## File Structure

```
docs/                        ← Instructions for coding assistant
├── 00-OVERVIEW.md           ← This file
├── 01-ARCHITECTURE.md       ← Technical architecture
├── 02-PIPELINE.md           ← Daily flow details
├── 03-BACKEND.md            ← Implementation guide
├── 04-FRONTEND.md           ← Frontend design guide
├── 05-DEPLOYMENT.md         ← Deploy steps
├── 06-SKILLS.md             ← Compiled skill references
├── 07-TASKS.md              ← Ordered implementation tasks
└── FRONTEND-DESIGN.md       ← Complete design system

backend/
├── main.py                  ← FastAPI + scheduler + routes
├── database.py              ← SQLite
├── requirements.txt
└── pipeline/
    ├── scrape.py            ← Multi-platform scraping
    ├── enrich.py            ← Resume/cover letter enrichment
    ├── contacts.py          ← Free contact finder
    ├── applier.py           ← Platform apply (Playwright) + Craigslist direct
    └── send.py              ← Email outreach

frontend/
└── index.html               ← Dashboard
```
