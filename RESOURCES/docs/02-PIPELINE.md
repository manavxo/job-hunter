# Pipeline — The 7-Step Daily Flow

---

## Step 1: Scrape (`pipeline/scrape.py`)

Search job boards for fresh postings matching the user's target roles and locations.

**Platforms supported:**
| Platform | Method |
|---|---|
| LinkedIn | jobspy (built-in) |
| Indeed | jobspy (built-in) |
| Glassdoor | jobspy (built-in) |
| Google Jobs | jobspy (built-in) |
| ZipRecruiter | jobspy (built-in) |
| Craigslist | Custom HTML scraper |

**Input:** `search` settings (job_titles, locations, platforms, hours_old, distance_miles)
**Output:** Deduplicated list of job dicts
**Error handling:** If one platform fails, continue with others.

---

## Step 2: Select

Score each job, exclude already-applied, pick top 10.

**Scoring (0-100):**
- Title match to target titles: 0–40
- Description length >200 chars: 15
- Has salary info: 15 (penalize if below minimum)
- Has apply URL: 10
- Has company name: 10
- Posted in last 6 hours: 10

**Deduplication:** Skip if (company, title) already in `jobs` table.

---

## Step 3: Enrich (`pipeline/enrich.py`) ★

**This is the core feature.** For each of the 10 selected jobs:

1. **Analyze the job description** — extract required skills, keywords, qualifications, experience level
2. **Compare to base resume** — identify gaps, strengths, transferable skills
3. **Generate tailored resume** — based on the selected mode (honest or enhanced)
4. **Generate tailored cover letter** — specific to this job, this company, this role
5. **Vary the format** — each of the 10 applications gets a different style so they don't look identical

### Resume Modes

#### Honest Mode
The LLM optimizes what's already there:
- Reorder bullets so the most relevant experience comes first
- Mirror keywords from the job description naturally
- Strengthen action verbs (managed → led, helped → delivered)
- Quantify accomplishments where possible
- Adjust professional summary for each role
- Improve formatting for ATS readability
- **Does NOT add experience or skills the user doesn't have**

#### Enhanced Mode
The LLM strategically fills gaps:
- Everything from honest mode, PLUS:
- Add relevant skills the job requires (even if not in base resume)
- Embellish accomplishments with plausible metrics
- Reframe existing experience to match the job's language
- Add project details that align with the role's requirements
- Expand job descriptions to cover more of the JD's keywords
- **Still realistic enough to pass ATS and not raise red flags**

### Context-Driven Customization

Every LLM call includes full context:

```
JOB CONTEXT:
- Title: {job_title}
- Company: {company}
- Description: {full JD}
- Required skills: {extracted from JD}
- Nice-to-have skills: {extracted from JD}
- Experience level: {extracted from JD}

CANDIDATE CONTEXT:
- Name: {name}
- Current resume: {base_resume}
- Target role: {title_target}
- Location: {location}

INSTRUCTIONS:
- Mode: {honest|enhanced}
- Style variant: {1-10} (ensures variety across daily batch)
- ATS optimization: mirror keywords, use standard section headers
- Format: clean markdown, one page equivalent
```

### Variety System

Each of the 10 daily applications gets a style variant (1-10) that changes:
- **Resume:** Section ordering, bullet point phrasing, professional summary angle
- **Cover letter:** Opening hook, achievement focus, closing style
- **Format:** Some use "Professional Summary" first, others lead with "Core Competencies"

This ensures no two applications look identical even when applying to similar roles.

**Input:** Selected jobs + base resume + base cover letter + LLM config + resume mode
**Output:** Per job: `{tailored_resume, tailored_cover_letter, style_variant}`

---

## Step 4: Find Contacts (`pipeline/contacts.py`)

Free hiring manager lookup. No paid API.

**5-layer fallback:**
1. Extract email from job description
2. Extract company domain from job URL
3. Web search for hiring manager names (DuckDuckGo)
4. Generate email permutations + SMTP verify
5. Generic emails (hr@, careers@, recruiting@)

---

## Step 5: Apply (`pipeline/applier.py`)

Submit through the platform or reach out directly.

**Flow A — Platform Apply (LinkedIn, Indeed, Glassdoor):**
Playwright browser automation: login → navigate → click Apply → fill form → submit.

**Flow B — Direct Contact (Craigslist):**
Craigslist posts have no portal. The post contains contact info:
- Email found → send personalized email with resume
- Phone found → log for manual follow-up
- "Text" mentioned → log for SMS
- Nothing found → log for manual review

**Anti-bot handling:**
- LinkedIn CAPTCHA/2FA → log as `blocked`, fall back to email
- Form too complex → log as `partial`

---

## Step 6: Email Outreach (`pipeline/send.py`)

Send personalized email to the hiring manager. This runs for EVERY job regardless of whether Step 5 succeeded. It's a second channel — platform apply + direct email = maximum coverage.

**Email structure:**
```
To: {hiring_manager_email}
Subject: Application: {job_title} at {company} — {candidate_name}

Dear {contact_name},

{tailored_cover_letter}

---
{signature}
Resume attached
LinkedIn: {linkedin_url}
```

---

## Step 7: Log

Record everything in `applications` table:
- Which resume + cover letter were sent
- Which method was used (linkedin_apply, indeed_apply, craigslist_email, etc.)
- Apply status + outreach status (tracked separately)
- Contact info and source
- Error messages if any

**Deduplication:** `jobs.status` tracks whether we've applied. Never re-applies.

---

## Pipeline Error Handling

| Failure | Response |
|---|---|
| Scrape fails | Abort pipeline, log error |
| No jobs found | Exit gracefully |
| Enrichment (LLM) fails | Use base resume + template cover letter |
| Contact lookup fails | Use fallback email (hr@domain) |
| Platform apply blocked | Log as blocked, still send email outreach |
| Email send fails | Log as failed, continue with next job |
| Individual job failure | Never abort the pipeline — continue with remaining jobs |
