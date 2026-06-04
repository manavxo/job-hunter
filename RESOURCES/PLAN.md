# Job Hunter — Automated Job Application System

> Scrapes 10 fresh project management jobs daily, customizes resume + cover letter for each, finds the hiring manager via Apollo, and sends personalized email outreach.

---

## Mission

Maximize interview callbacks by combining volume (10/day) with quality (customized materials + direct hiring manager contact). Every application is personalized, every outreach is targeted.

---

## Architecture

```
8:00 AM Daily
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  1. SCRAPE  (tools/scrape_jobs.py)                   │
│     - jobspy → LinkedIn, Indeed, Glassdoor, Google   │
│     - Filter: last 24h, project management, location │
│     - Output: .tmp/today_jobs.json                   │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  2. SELECT  (tools/select_top_10.py)                 │
│     - Dedupe against applications.log                │
│     - Score by relevance (title match, salary, recency)│
│     - Pick top 10                                    │
│     - Output: .tmp/selected_jobs.json                │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  3. FIND CONTACT  (tools/apollo_lookup.py)           │
│     - Apollo API → find hiring manager               │
│     - Fallback: company careers email from job post  │
│     - Output: .tmp/applications/{id}_contact.json    │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  4. CUSTOMIZE  (tools/customize_materials.py)        │
│     - LLM tailors resume + cover letter per job      │
│     - Mirrors JD keywords, reorders experience       │
│     - Output: .tmp/applications/{id}_resume.md       │
│     - Output: .tmp/applications/{id}_cover.md        │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  5. PDF  (tools/generate_pdf.py)                     │
│     - Convert markdown resumes to clean PDFs         │
│     - Output: .tmp/applications/{id}_resume.pdf      │
└──────────────┬───────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────┐
│  6. SEND  (tools/send_outreach.py)                   │
│     - Compose personalized email                     │
│     - Send via Gmail SMTP with resume attached       │
│     - Log to applications.log                        │
└──────────────────────────────────────────────────────┘
```

---

## Tech Stack (all free or near-free)

| Component | Tool | Cost |
|---|---|---|
| Job scraping | `jobspy` Python library | Free |
| Resume customization | OpenRouter API (any LLM) | ~$0.01/app |
| Hiring manager lookup | Apollo.io API | Free (50/mo) |
| Email sending | Gmail SMTP | Free |
| PDF generation | `weasyprint` + `markdown2` | Free |
| Scheduling | OS cron / Task Scheduler | Free |

---

## Files

| File | Purpose |
|---|---|
| `config.yaml` | All settings in one place |
| `base_resume.md` | Master resume (LLM copies from this) |
| `base_cover_letter.md` | Master cover letter template |
| `applications.log` | JSONL log of every application sent |
| `tools/setup_wizard.py` | Interactive setup + connection testing |
| `tools/scrape_jobs.py` | Job scraping via jobspy |
| `tools/select_top_10.py` | Score, dedupe, select best 10 |
| `tools/apollo_lookup.py` | Apollo API hiring manager lookup |
| `tools/customize_materials.py` | LLM resume + cover letter tailoring |
| `tools/generate_pdf.py` | Markdown → PDF conversion |
| `tools/send_outreach.py` | Email composition + sending |
| `tools/daily_hunt.py` | Full pipeline orchestrator |
| `workflows/daily-hunt.md` | SOP for the daily run |
| `.tmp/` | Temporary processing (regenerated daily) |

---

## Setup

```bash
pip install -r requirements.txt
python tools/setup_wizard.py     # interactive setup
python tools/daily_hunt.py --skip-send  # dry run
```

---

## Apollo Credit Strategy

| Month | Jobs/day | Monthly apps | Apollo needed | Strategy |
|---|---|---|---|---|
| Free tier | 10 | ~220 | 50 credits | Use Apollo for top 50, fallback for rest |
| Paid ($49/mo) | 10 | ~220 | Unlimited | All apps get direct hiring manager email |

**Recommendation:** Start free. If the first 50 Apollo-enriched emails get better response rates, upgrade.
