# Workflow: Daily Job Hunt

> Orchestrates the full daily job application pipeline — scrape, select, find contacts, customize, generate PDFs, send outreach. Runs at 8:00 AM via OS scheduler.

---

## Objective

Each morning, find 10 fresh project management jobs posted in the last 24 hours, customize a resume and cover letter for each, identify the hiring manager, and send a personalized email pitch. All applications logged.

---

## Inputs

| Input | Where to get it | Example |
|---|---|---|
| `config.yaml` | Project root | Filled with candidate profile, search params, API keys |
| `base_resume.md` | Project root | Candidate's master resume |
| `base_cover_letter.md` | Project root | Cover letter template |
| LLM API key | In config.yaml | `llm.api_key` (OpenRouter, OpenAI, etc.) |
| Apollo API key | In config.yaml | `apollo.api_key` (optional) |
| Gmail credentials | In config.yaml | `email.username` + `email.password` (App Password) |

---

## Tools to Use

1. `tools/scrape_jobs.py` — Scrapes LinkedIn, Indeed, Glassdoor, Google Jobs via `jobspy`
2. `tools/select_top_10.py` — Scores, dedupes, selects best 10 jobs
3. `tools/apollo_lookup.py` — Finds hiring manager via Apollo API
4. `tools/customize_materials.py` — LLM tailors resume + cover letter per job
5. `tools/generate_pdf.py` — Converts markdown resumes to PDF
6. `tools/send_outreach.py` — Sends personalized emails via Gmail SMTP
7. `tools/daily_hunt.py` — Orchestrator that calls all of the above

---

## Steps

### 1. Scrape Jobs
```bash
python tools/scrape_jobs.py
```
- Searches all configured job titles × locations
- Filters to jobs posted in last 24 hours
- Dedupes by (title, company)
- Saves to `.tmp/today_jobs.json`

### 2. Select Top 10
```bash
python tools/select_top_10.py
```
- Loads `.tmp/today_jobs.json`
- Removes already-applied (checks `applications.log`)
- Scores by relevance (title match, salary info, recency)
- Picks top 10
- Saves to `.tmp/selected_jobs.json`

### 3. Find Hiring Managers
```bash
python tools/apollo_lookup.py
```
- For each of the 10 jobs, queries Apollo API
- Finds recruiter, hiring manager, or HR contact
- Saves contact + job info to `.tmp/applications/{id}_contact.json` and `{id}_job.json`
- Falls back to email extracted from job description or generic HR email

### 4. Customize Resume & Cover Letter
```bash
python tools/customize_materials.py
```
- For each job, reads the description + base resume
- Calls LLM to tailor resume bullets, reorder experience, mirror JD keywords
- Calls LLM to write a fresh cover letter referencing specific requirements
- Saves to `.tmp/applications/{id}_resume.md` and `{id}_cover.md`

### 5. Generate PDFs
```bash
python tools/generate_pdf.py
```
- Converts each `{id}_resume.md` to a clean, professional PDF
- Falls back to HTML if weasyprint not installed
- Output: `.tmp/applications/{id}_resume.pdf`

### 6. Send Emails
```bash
python tools/send_outreach.py
```
- Reads each application's job, contact, cover letter, resume
- Composes personalized email with subject line
- Sends via Gmail SMTP with resume PDF attached
- Logs to `applications.log`

---

## Orchestration

Run the full pipeline:
```bash
python tools/daily_hunt.py              # full run
python tools/daily_hunt.py --skip-send  # dry run (no emails)
```

---

## Expected Output

- **10 emails sent** to hiring managers/recruiters
- **10 applications logged** in `applications.log` (JSONL format)
- **`.tmp/applications/`** contains all generated materials (resumes, cover letters, PDFs, contacts)
- Each email has: personalized subject, tailored cover letter body, resume PDF attached

---

## Edge Cases & Gotchas

- **Apollo credits exhausted:** Falls back to email extracted from job description or `hr@company.com`. Still sends, but lower response rate.
- **No email found:** Job is logged as `skipped_no_email` and not sent.
- **Duplicate application:** Checked against `applications.log` by (company, title). Won't re-apply.
- **jobspy rate limiting:** Built-in 1s delay between searches. If blocked, try fewer search terms.
- **Gmail sending limits:** 10/day is well within limits (500/day for consumer Gmail).
- **Job description too short:** LLM customization still works but output quality depends on JD length.
- **LLM API down:** Pipeline uses base resume + template cover letter as fallback.
- **Costs:** jobspy = free, LLM = ~$0.01/app, Apollo = 50 free/month, Gmail SMTP = free.
