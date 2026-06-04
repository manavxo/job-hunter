# Multi-User / Multi-Profile Provisions

> Reference document for future development. When you're ready to serve multiple users, this is what needs to change — layer by layer.

---

## 1. Database Layer (`backend/database.py`)

### Current State
- `settings` table: flat key-value store with `key TEXT PRIMARY KEY`. All settings (candidate, search, LLM, email, resume, cover letter) are global rows with no user association.
- `jobs` table: no `profile_id` column. Jobs are globally shared.
- `applications` table: no `profile_id` column. Application history is global.
- Duplicate check in `insert_jobs()` uses `(company, title)` globally — two profiles scraping the same job would collide.

### Changes Needed

```sql
-- New table
CREATE TABLE profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    is_active BOOLEAN DEFAULT 1
);

-- Add profile_id to existing tables
ALTER TABLE jobs ADD COLUMN profile_id INTEGER REFERENCES profiles(id);
ALTER TABLE applications ADD COLUMN profile_id INTEGER REFERENCES profiles(id);

-- Settings becomes per-profile
CREATE TABLE profile_settings (
    profile_id INTEGER REFERENCES profiles(id),
    key TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (profile_id, key)
);
```

### Functions to Update
- `get_setting()` / `set_setting()` — add `profile_id` parameter
- `get_all_settings()` — scope to profile
- `insert_jobs()` — add `profile_id`, dedupe per-profile
- `insert_application()` — add `profile_id`
- `get_new_jobs()` — scope to profile
- `get_application_history()` — scope to profile
- `get_application_stats()` — scope to profile

---

## 2. API Layer (`backend/main.py`)

### Endpoints Needing Profile Scoping

| Endpoint | Change |
|---|---|
| `GET /api/settings` | Add `?profile_id=X` query param |
| `PUT /api/settings` | Add `profile_id` to body or query |
| `GET /api/jobs` | Scope to profile |
| `GET /api/jobs/new` | Scope to profile |
| `GET /api/applications` | Scope to profile |
| `GET /api/applications/stats` | Scope to profile |
| `POST /api/pipeline/run` | Add `profile_id` param |
| `POST /api/pipeline/scrape` | Add `profile_id` param |
| `GET /api/schedule` | Per-profile schedule |
| `PUT /api/schedule` | Per-profile schedule |

### New Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/profiles` | List all profiles |
| `POST` | `/api/profiles` | Create profile |
| `PUT` | `/api/profiles/{id}` | Update profile |
| `DELETE` | `/api/profiles/{id}` | Delete profile |
| `GET` | `/api/profiles/{id}/settings` | Get profile settings |
| `PUT` | `/api/profiles/{id}/settings` | Update profile settings |

### Pipeline Change
```python
# Current: runs once globally
run_daily_pipeline()

# Future: loop over all active profiles
for profile in db.get_active_profiles():
    run_daily_pipeline(profile_id=profile["id"])
```

---

## 3. Frontend (`frontend/index.html`)

### Changes Needed
- **Profile selector** in the header (dropdown or tab)
- **Profile management** section in Settings (create/edit/delete profiles)
- **Dashboard stats** scoped to selected profile
- **Jobs table** filtered by profile
- **Applications table** filtered by profile
- **Schedule** per-profile (each profile can have its own run time)
- **Resume/Cover letter** stored per-profile in settings

### Data Flow
```
User selects profile → API calls include profile_id → DB queries scoped → Results displayed
```

---

## 4. Pipeline Modules

### `pipeline/scrape.py`
- `scrape_jobs()` — no change (scraping is profile-agnostic)
- `score_job()` — no change (scoring uses target titles from config)
- Jobs saved with `profile_id` tag

### `pipeline/contacts.py`
- `find_contact()` — no change (contact lookup is per-job, not per-profile)

### `pipeline/enrich.py`
- `customize_resume()` — reads profile-specific resume template
- `customize_cover_letter()` — reads profile-specific cover letter template

### `pipeline/send.py`
- `send_email()` — uses profile-specific SMTP credentials
- `compose_email()` — uses profile-specific signature

### Error Isolation
```python
for profile in db.get_active_profiles():
    try:
        run_daily_pipeline(profile_id=profile["id"])
    except Exception as e:
        logger.error("Profile %s failed: %s", profile["id"], e)
        continue  # Don't let one profile failure stop others
```

---

## 5. Role Templates (Future Enhancement)

### Template Structure
```yaml
# templates/healthcare.yaml
name: "Healthcare / Clinical"
default_job_titles:
  - "Physical Therapist"
  - "Kinesiologist"
  - "Clinical Coordinator"
  - "Rehabilitation Specialist"
default_resume_sections:
  - "Clinical Experience"
  - "Certifications & Licenses"
  - "Patient Outcomes"
default_competencies:
  - "Patient Care"
  - "Clinical Assessment"
  - "Treatment Planning"
  - "EMR Systems"
```

### Template Directory
```
templates/
├── corporate-pm.yaml
├── healthcare.yaml
├── engineering.yaml
├── education.yaml
├── creative.yaml
└── custom.yaml
```

### Implementation
- Templates are read-only presets
- User picks template when creating a profile
- Template pre-fills search config, resume structure, competencies
- User can customize everything after template selection

---

## 6. File Organization

### Current
```
base_resume.md          ← single global
base_cover_letter.md    ← single global
config.yaml             ← single global
```

### Future
```
profiles/
├── 1/                  ← Profile 1 (e.g., friend's PM profile)
│   ├── resume.md
│   ├── cover_letter.md
│   └── config.yaml
├── 2/                  ← Profile 2 (e.g., girlfriend's kinesiology profile)
│   ├── resume.md
│   ├── cover_letter.md
│   └── config.yaml
base_resume.md          ← kept as fallback template
base_cover_letter.md    ← kept as fallback template
```

---

## 7. Migration Path

### Step 1: Add profiles table
```sql
INSERT INTO profiles (id, name) VALUES (1, 'Default');
```

### Step 2: Migrate existing settings
```sql
-- Copy all current settings to profile_settings with profile_id=1
INSERT INTO profile_settings (profile_id, key, value)
SELECT 1, key, value FROM settings;
```

### Step 3: Tag existing data
```sql
UPDATE jobs SET profile_id = 1 WHERE profile_id IS NULL;
UPDATE applications SET profile_id = 1 WHERE profile_id IS NULL;
```

### Step 4: Update all API endpoints to require profile_id
### Step 5: Update frontend with profile selector
### Step 6: Add profile CRUD endpoints
### Step 7: Add role templates

**Zero data loss** — existing single-user data becomes Profile 1.