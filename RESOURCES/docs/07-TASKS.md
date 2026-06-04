# Implementation Tasks

Ordered. Each task is 2-5 minutes. Read the referenced doc before each task.

---

## Phase 1: Backend Core

### Task 1: database.py
**File:** `backend/database.py`
**Ref:** `docs/01-ARCHITECTURE.md` (schema)

SQLite module: `get_db()`, `init_db()`, `get_setting()`, `set_setting()`, `get_all_settings()`, `insert_jobs()`, `get_new_jobs()`, `mark_job_status()`, `insert_application()`, `get_application_history()`, `get_application_stats()`.

Three tables: settings, jobs, applications. Settings is key-value with JSON-encoded values.

**Verify:** `python -c "import database; database.init_db(); print('OK')"`

### Task 2: pipeline/scrape.py
**File:** `backend/pipeline/scrape.py`
**Ref:** `docs/02-PIPELINE.md` (Step 1)

Multi-platform scraper with region support. Functions: `scrape_jobs(search_config)`, `score_job()`, `get_available_platforms()`.

Platforms: LinkedIn, Indeed, Glassdoor, Google, ZipRecruiter (via jobspy), Craigslist (custom HTML scraper). Region maps to `country_indeed` parameter.

**Verify:** `python -c "from pipeline.scrape import get_available_platforms; print(len(get_available_platforms()))"`

### Task 3: pipeline/enrich.py ★
**File:** `backend/pipeline/enrich.py`
**Ref:** `docs/02-PIPELINE.md` (Step 3)

The core personalization module. Functions:
- `call_llm(llm_config, system, user)` — OpenAI-compatible API
- `enrich_application(job, base_resume, base_cover, candidate, llm_config, resume_mode, style_index)` — main entry
- `_analyze_job(jd, llm_config)` — extract skills, keywords, ATS terms from JD as JSON
- `_generate_resume(...)` — honest or enhanced, with style variant
- `_generate_cover_letter(...)` — tailored to job + company + variant
- `get_style_variant(index)` — 10 variants for variety

**Resume modes:**
- `honest` — reorder, mirror keywords, strengthen verbs, no fabrication
- `enhanced` — add skills, embellish, fill gaps, reframe experience

**10 style variants:** achievement-focused, skills-forward, leadership-angle, problem-solver, results-driven, collaborative, innovation-focused, client-centric, strategic, delivery-focused

**Verify:** `python -c "from pipeline.enrich import get_style_variant; print(get_style_variant(3)['name'])"`

### Task 4: pipeline/contacts.py
**File:** `backend/pipeline/contacts.py`
**Ref:** `docs/02-PIPELINE.md` (Step 4)

Free contact finder: `find_contact(job)`. DuckDuckGo search + email permutation + SMTP verify.

**Verify:** `python -c "from pipeline.contacts import find_contact; print('OK')"`

### Task 5: pipeline/applier.py
**File:** `backend/pipeline/applier.py`
**Ref:** `docs/02-PIPELINE.md` (Step 5)

Platform apply + Craigslist direct contact. Functions: `apply_to_job()`, `get_platform()`.

- **LinkedIn/Indeed/Glassdoor:** Playwright logs in with stored credentials → fills form → submits
- **Craigslist:** Extract email/phone from post → send email directly
- **External:** Browser form fill → email fallback

Credentials come from `settings["platform_credentials"]` — user pre-creates accounts.

**Verify:** `python -c "from pipeline.applier import get_platform; print(get_platform('https://linkedin.com/jobs/123'))"`

### Task 6: pipeline/send.py
**File:** `backend/pipeline/send.py`
**Ref:** `docs/02-PIPELINE.md` (Step 6)

Email outreach via Gmail SMTP. `send_email()`, `compose_email()`.

**Verify:** `python -c "from pipeline.send import compose_email; print('OK')"`

### Task 7: main.py
**File:** `backend/main.py`
**Ref:** `docs/03-BACKEND.md`

FastAPI app. All routes, APScheduler, `run_daily_pipeline()` orchestrator, static files.

Pipeline calls `enrich.enrich_application()` with `resume_mode` from settings and `style_index=i` for variety.

**Verify:** `uvicorn main:app --port 8000` → `curl localhost:8000/api/health`

---

## Phase 2: Frontend

### Task 8: frontend/index.html — Shell
**File:** `frontend/index.html`
**Ref:** `docs/FRONTEND-DESIGN.md`

HTML skeleton: Google Fonts (Inter), CSS custom properties, nav tabs, tab containers, JS switching.

### Task 9: Dashboard tab
Stats row (4 cards), schedule card, recent applications table.

### Task 10: Jobs tab
"Scrape Now" button, jobs table.

### Task 11: Applications tab
Full history table.

### Task 12: Settings tab
**Ref:** `docs/01-ARCHITECTURE.md` (settings keys)

Forms:
- Candidate profile
- Job search (titles, locations, **platform checkboxes** from `/api/platforms`, **region dropdown**)
- **Resume mode** (radio: Honest / Enhanced with descriptions)
- **Platform credentials** (one email+password field per selected platform)
- LLM config
- Email config
- Resume textarea
- Cover letter textarea

### Task 13: Polish
Empty states, toasts, responsive, verification checklist.

---

## Phase 3: Deploy

### Task 14: Deploy to Railway
Push to GitHub, connect Railway, add volume, set `DB_PATH`.

---

## Phase 4: Test

### Task 15: End-to-end
Settings → Scrape → Run → Verify applications → Check email.
