# Job Hunter

> Automated daily job application system. Scrapes 10 fresh PM jobs each morning, customizes resume + cover letter per role, finds hiring managers via Apollo, and sends personalized email outreach.

---

## Customer

Friend looking for a project management role. Wants to maximize interview callbacks through volume (10/day) + quality (customized materials + direct hiring manager contact).

---

## Pipeline Stages Active

| Stage | Active? | Notes |
|---|---|---|
| FIND | yes | `jobspy` scrapes LinkedIn, Indeed, Glassdoor, Google Jobs |
| SHAPE | yes | Score, dedupe, filter, select top 10 |
| BUILD | yes | LLM customizes resume + cover letter per job |
| SHIP | yes | Gmail SMTP with PDF resume attached |
| REACH | yes | Apollo API for hiring manager lookup |

---

## Global Skills Used

- `himalaya` — Email sending via SMTP (reference)
- `humanizer` — Strip AI-isms from generated cover letters

---

## Local Tools

- `tools/setup_wizard.py` — Interactive setup + connection testing
- `tools/scrape_jobs.py` — Multi-source job scraping via jobspy
- `tools/select_top_10.py` — Score, dedupe, select best 10
- `tools/apollo_lookup.py` — Apollo.io hiring manager lookup
- `tools/customize_materials.py` — LLM resume + cover letter tailoring
- `tools/generate_pdf.py` — Markdown → PDF conversion
- `tools/send_outreach.py` — Email composition + SMTP sending
- `tools/daily_hunt.py` — Full pipeline orchestrator

---

## Key Outputs

| Output | Location |
|---|---|
| Today's jobs | `.tmp/today_jobs.json` |
| Selected 10 | `.tmp/selected_jobs.json` |
| Applications | `.tmp/applications/` (resumes, cover letters, PDFs, contacts) |
| Application log | `applications.log` (JSONL — every app sent) |

---

## Daily Schedule

Runs via OS scheduler (cron / Task Scheduler). The pipeline:
1. Runs `daily_hunt.py` which calls all tools in sequence
2. Scrape → Select → Contact lookup → Customize → PDF → Send

## Config

All settings in `config.yaml`. Must be filled before first run:
- Candidate profile (name, email, phone, LinkedIn)
- Search parameters (titles, locations, salary)
- LLM API key (OpenRouter or any OpenAI-compatible)
- Apollo API key (optional)
- Gmail SMTP credentials
