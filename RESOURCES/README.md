# Job Hunter

Automated daily job application system. Scrapes 10 fresh project management jobs every morning, customizes a resume and cover letter for each, finds the hiring manager, and sends a personalized email pitch.

---

## Quick Start (3 steps)

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. Set up
```bash
python tools/setup_wizard.py
```
The wizard asks for your details, API keys, and tests everything works.

### 3. Run
```bash
# Dry run first (no emails sent)
python tools/daily_hunt.py --skip-send

# When ready, run for real
python tools/daily_hunt.py
```

---

## What You Need

| Item | Where to get it | Required? |
|---|---|---|
| **Your resume** | Paste your content into `base_resume.md` | Yes |
| **OpenRouter API key** | https://openrouter.ai/keys (free credits available) | Yes |
| **Gmail App Password** | Google Account → Security → 2FA → App Passwords | Yes |
| **Apollo.io API key** | https://apollo.io → Settings → API Keys (50 free/month) | Optional |

---

## What Happens Every Day

At 8:00 AM (or whenever you run it):

1. **Scrapes** LinkedIn, Indeed, Glassdoor, Google Jobs for PM roles posted in last 24h
2. **Selects** top 10 by relevance (title match, salary, recency)
3. **Finds** the hiring manager via Apollo.io (falls back to job description emails)
4. **Customizes** your resume and cover letter for each specific job using AI
5. **Generates** clean PDF resumes
6. **Sends** personalized emails with resume attached
7. **Logs** everything to `applications.log` (never re-applies to the same job)

---

## Files to Edit

| File | What to put in it |
|---|---|
| `base_resume.md` | Your full resume in markdown. The AI reorders/tailors it per job. |
| `base_cover_letter.md` | Your cover letter template. The AI writes a fresh one per job. |
| `config.yaml` | Filled by setup wizard. You can also edit manually. |

---

## Scheduling (Optional)

### Windows Task Scheduler
```bash
# Create a batch file run_job_hunter.bat:
cd /d "C:\path\to\job-hunter"
python tools\daily_hunt.py
```
Schedule it to run daily at 8:00 AM.

### Linux/Mac Cron
```bash
crontab -e
# Add: 0 8 * * * cd /path/to/job-hunter && python tools/daily_hunt.py
```

---

## Customization

### Change search terms
Edit `config.yaml` → `search.job_titles` and `search.locations`

### Change daily limit
Edit `config.yaml` → `search.jobs_per_day` (default: 10)

### Change LLM model
Edit `config.yaml` → `llm.model` (any OpenAI-compatible model)

### Exclude companies
Edit `config.yaml` → `search.excluded_companies`

---

## How It Works

```
8:00 AM
    │
    ▼
 SCRAPE ─── jobspy → LinkedIn, Indeed, Glassdoor, Google
    │         Filter: last 24h, project management
    ▼
 SELECT ─── Dedupe against applications.log
    │         Score by relevance, pick top 10
    ▼
 CONTACT ── Apollo API → find hiring manager email
    │         Fallback: extract from job description
    ▼
 CUSTOMIZE ─ LLM tailors resume + cover letter per job
    │          Keywords, reordering, company-specific hooks
    ▼
 PDF ─────── Generate clean PDF resumes
    │
    SEND ──── Personalized email via Gmail SMTP
    │          Resume attached, logged to applications.log
    ▼
 DONE (10 applications sent)
```

---

## FAQ

**Q: Will this get my account banned?**
A: 10 emails/day is well within Gmail's limits (500/day). Job board scraping uses public data.

**Q: What if there aren't 10 new jobs?**
A: It sends however many pass the filter. Some days might be 5, some might be 15 (if you increase the limit).

**Q: Can I use this for non-PM roles?**
A: Yes. Edit `config.yaml` → `search.job_titles` to anything. The system is role-agnostic.

**Q: What if Apollo runs out of credits?**
A: It falls back to extracting emails from job descriptions or using `hr@company.com`. You can also skip Apollo entirely.

**Q: How much does this cost?**
A: ~$0-2/month. OpenRouter is pay-per-use (~$0.01 per application), Apollo has a free tier, Gmail SMTP is free.

---

## Tech Stack

- **Python 3.9+** — all tools
- **jobspy** — multi-site job scraping
- **OpenRouter / OpenAI API** — resume + cover letter customization
- **Apollo.io** — hiring manager lookup
- **Gmail SMTP** — email sending
- **weasyprint** — PDF generation
- **pyyaml** — configuration
