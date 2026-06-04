# Backend Implementation Guide

## Dependencies

```
fastapi>=0.104.0
uvicorn>=0.24.0
apscheduler>=3.10.0
python-jobspy>=1.1.0
pyyaml>=6.0
requests>=2.28.0
dnspython>=2.4.0
python-multipart>=0.0.6
playwright>=1.40.0
```

## Pipeline Modules

### `pipeline/enrich.py` — Resume & Cover Letter Enrichment

The core personalization engine. Replaces the old `customize.py`.

```python
def enrich_application(job, base_resume, base_cover, candidate, llm_config,
                       resume_mode="honest", style_index=0) -> dict:
    """
    Returns: {resume, cover_letter, style_variant, skills_matched, gaps_filled}
    """
```

**Key functions:**
- `call_llm(llm_config, system_prompt, user_prompt)` — OpenAI-compatible API call
- `_analyze_job(jd, llm_config)` — Extract skills, keywords, requirements from JD
- `_generate_resume(...)` — Tailored resume (honest or enhanced)
- `_generate_cover_letter(...)` — Tailored cover letter
- `get_style_variant(index)` — Get style variant (0-9) for variety

**Style variants:** 10 different approaches (achievement-focused, skills-forward, leadership-angle, problem-solver, results-driven, collaborative, innovation-focused, client-centric, strategic, delivery-focused). Each application gets a different variant.

### `pipeline/scrape.py` — Multi-Platform Scraping

```python
def scrape_jobs(search_config) -> list[dict]
def score_job(job, target_titles, min_salary) -> int
def get_available_platforms() -> list[dict]
```

Supports: LinkedIn, Indeed, Glassdoor, Google, ZipRecruiter, Craigslist (custom scraper).

### `pipeline/contacts.py` — Free Contact Finder

```python
def find_contact(job) -> dict
```

DuckDuckGo search + email permutation + SMTP verification. No paid API.

### `pipeline/applier.py` — Platform Apply + Direct Contact

```python
def apply_to_job(job, credentials, candidate, email_config,
                 resume_path, cover_letter) -> dict
```

Two flows:
- **Platform apply** (LinkedIn, Indeed): Playwright browser automation
- **Direct contact** (Craigslist): Email/SMS/phone extracted from post

### `pipeline/send.py` — Email Outreach

```python
def send_email(email_config, to_email, subject, body, attachment_path) -> bool
def compose_email(job, contact, cover_letter, candidate, email_config) -> tuple
```

## Entry Point: `main.py`

### Pipeline Orchestrator

```python
def run_daily_pipeline():
    settings = db.get_all_settings()
    candidate = settings["candidate"]
    search_config = settings["search"]
    llm_config = settings["llm"]
    email_config = settings["email"]
    base_resume = settings["base_resume"]
    base_cover = settings["base_cover_letter"]
    resume_mode = settings.get("resume_mode", "honest")

    # 1. Scrape
    raw_jobs = scrape.scrape_jobs(search_config)
    for job in raw_jobs:
        job["relevance_score"] = scrape.score_job(job, search_config["job_titles"],
                                                   search_config.get("min_salary", 0))
    db.insert_jobs(raw_jobs)

    # 2. Select
    selected = db.get_new_jobs(search_config.get("jobs_per_day", 10))

    # 3-7. For each job
    for i, job in enumerate(selected):
        # 3. Enrich (with style variant)
        enrichment = enrich.enrich_application(
            job, base_resume, base_cover, candidate, llm_config,
            resume_mode=resume_mode, style_index=i
        )

        # 4. Find contact
        contact = contacts.find_contact(job)

        # 5. Apply through platform
        apply_result = applier.apply_to_job(
            job, credentials, candidate, email_config,
            resume_path=None, cover_letter=enrichment["cover_letter"]
        )

        # 6. Email outreach (always runs)
        subject, body = send.compose_email(
            job, contact, enrichment["cover_letter"], candidate, email_config
        )
        send.send_email(email_config, contact["email"], subject, body)

        # 7. Log
        db.insert_application(...)
```

### Scheduler

```python
scheduler = BackgroundScheduler()
scheduler.add_job(run_daily_pipeline, "cron", hour=8, minute=0)
scheduler.start()
```

Schedule is configurable via the dashboard.

## Running Locally

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --port 8000
```

Dashboard: http://localhost:8000
API docs: http://localhost:8000/docs
