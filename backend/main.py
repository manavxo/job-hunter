"""
Job Hunter — FastAPI web app with built-in scheduler.

Runs the daily job application pipeline on a schedule and exposes a REST API
for the dashboard. The pipeline:

    scrape -> select -> enrich -> find contact -> apply -> (best-effort) outreach -> log

Every job is *applied to*. A tailored email to the hiring manager is a best-effort
second channel: it only fires when a reasonably reliable contact email is found.

Multi-profile support: each user gets their own jobs, applications, settings,
resume, cover letter, and schedule. Access code gate prevents unauthorized access.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database as db
from pipeline import scrape, enrich, contacts, applier, send, resume_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobhunter")

# Platforms that the applier logs into with stored credentials.
LOGIN_PLATFORMS = ("linkedin", "indeed", "glassdoor")

# In-memory session tokens: {token: {"profile_id": int, "created": float}}
_sessions: dict[str, dict] = {}
SESSION_TTL = 86400  # 24 hours

# Role templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
scheduler = BackgroundScheduler()


def _flatten_credentials(platform_credentials: dict) -> dict:
    """
    Convert nested {linkedin: {email, password}, ...} into the flat keys the
    applier expects: {linkedin_email, linkedin_password, ...}.
    """
    creds: dict = {}
    for platform, info in (platform_credentials or {}).items():
        if isinstance(info, dict):
            creds[f"{platform}_email"] = info.get("email", "")
            creds[f"{platform}_password"] = info.get("password", "")
    return creds


# ---------------------------------------------------------------------------
# Access Code Auth
# ---------------------------------------------------------------------------
def _check_access_code_enabled() -> bool:
    """Check if access code protection is enabled."""
    code = db.get_setting("access_code")
    env_code = os.environ.get("ACCESS_CODE")
    return bool(code or env_code)


def _verify_access_code(code: str) -> bool:
    """Verify the provided access code against stored/env code."""
    stored = db.get_setting("access_code")
    env_code = os.environ.get("ACCESS_CODE")
    expected = stored or env_code
    if not expected:
        return True  # No code set = open access
    return secrets.compare_digest(str(code).strip(), str(expected).strip())


def _create_session(profile_id: int) -> str:
    """Create a session token for an authenticated user."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = {"profile_id": profile_id, "created": time.time()}
    return token


def _validate_session(request: Request) -> Optional[int]:
    """
    Validate session token from Authorization header.
    Returns profile_id if valid, None if no auth required, raises if invalid.
    """
    if not _check_access_code_enabled():
        return 1  # No auth required, default to profile 1

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = auth[7:]
    session = _sessions.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    # Check TTL
    if time.time() - session["created"] > SESSION_TTL:
        _sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Session expired")

    return session["profile_id"]


def run_daily_pipeline(profile_id=None, simulate=False):
    """
    The daily pipeline — runs at the scheduled time (or on manual trigger).

    When simulate=True it runs every step (scrape, enrich, contact-find, PDF) and
    logs exactly what it *would* apply/email, but submits nothing and sends nothing.
    Use it to watch the whole flow safely.
    """
    pid = profile_id or 1
    mode = "SIMULATION (no apply, no email)" if simulate else "LIVE"
    profile = db.get_profile(pid)
    profile_name = profile.get("name", f"Profile {pid}") if profile else f"Profile {pid}"
    logger.info("=" * 60)
    logger.info("DAILY PIPELINE STARTED [%s] — Profile: %s (%d) — %s", mode, profile_name, pid, datetime.now().isoformat())
    logger.info("=" * 60)

    settings = db.get_all_settings(profile_id=pid)
    candidate = settings.get("candidate", {})
    if not candidate.get("name"):
        logger.warning("Pipeline skipped — candidate not configured for profile %d", pid)
        return

    search_config = settings.get("search", {})
    llm_config = settings.get("llm", {})
    email_config = settings.get("email", {})
    base_resume = settings.get("base_resume", "")
    base_cover = settings.get("base_cover_letter", "")
    resume_mode = settings.get("resume_mode", "honest")
    creds = _flatten_credentials(settings.get("platform_credentials", {}))
    email_ready = bool(email_config.get("username") and email_config.get("password"))

    # Load role template context for enrichment
    role_template = _load_role_template(profile.get("role_template", "general") if profile else "general")

    # Step 1: Scrape
    logger.info("Step 1: Scraping job boards...")
    try:
        raw_jobs = scrape.scrape_jobs(search_config)
        for job in raw_jobs:
            job["relevance_score"] = scrape.score_job(
                job, search_config.get("job_titles", []), search_config.get("min_salary", 0)
            )
        new_count = db.insert_jobs(raw_jobs, profile_id=pid)
        logger.info("  Scraped %d jobs, %d new", len(raw_jobs), new_count)
    except Exception as exc:  # noqa: BLE001 — scrape failure aborts the run
        logger.error("  Scrape failed: %s", exc)
        return

    # Step 2: Select top N
    jobs_per_day = search_config.get("jobs_per_day", 10)
    selected = db.get_new_jobs(jobs_per_day, profile_id=pid)
    logger.info("Step 2: Selected %d jobs", len(selected))
    if not selected:
        logger.info("  No new jobs. Pipeline done.")
        return

    applied_count = 0
    outreach_count = 0

    # Steps 3-7: per job. A failure in one job never aborts the batch.
    for i, job in enumerate(selected):
        title = (job.get("title") or "?")[:50]
        company = job.get("company") or "?"
        logger.info("  [%d/%d] %s at %s", i + 1, len(selected), title, company)

        try:
            # 3. Enrich (resume + cover letter, with a per-job style variant)
            enrichment = enrich.enrich_application(
                job, base_resume, base_cover, candidate, llm_config,
                resume_mode=resume_mode, style_index=i,
                role_template=role_template,
            )

            # PDF for upload / attachment (best-effort)
            resume_path = resume_pdf.render_resume_pdf(enrichment["resume"], candidate, job)

            # Cover letter PDF (best-effort)
            cover_path = resume_pdf.render_cover_letter_pdf(enrichment["cover_letter"], candidate, job)

            # 4. Find a contact (best-effort)
            try:
                contact = contacts.find_contact(job)
            except Exception as exc:  # noqa: BLE001
                logger.warning("    Contact lookup failed: %s", exc)
                contact = {"name": "", "email": "", "title": "", "source": "none"}

            logger.info("    Enriched: %s variant, resume %d chars%s",
                        enrichment.get("style_variant", "?"), len(enrichment["resume"]),
                        ", PDF ready" if resume_path else ", no PDF")

            # 5. Apply through the platform.
            apply_error = None
            if simulate:
                platform = applier.get_platform(job.get("job_url", ""))
                apply_status, apply_method = "simulated", f"would_apply:{platform}"
                logger.info("    [SIMULATE] would apply via %s", platform)
            else:
                apply_result = applier.apply_to_job(
                    job, creds, candidate, email_config,
                    resume_path=resume_path, cover_letter=enrichment["cover_letter"],
                )
                apply_status = apply_result.get("status", "unknown")
                apply_method = apply_result.get("method", "")
                apply_error = apply_result.get("error")
                if apply_status in ("applied", "partial"):
                    applied_count += 1
                logger.info("    Apply: %s (%s)", apply_status, apply_method)

            # 6. Outreach email — best-effort second channel.
            # Only fire when we have a reasonably reliable email (not a blind guess).
            outreach_status = "skipped"
            contact_email = contact.get("email", "")
            reliable = contact.get("source") in ("job_description", "verified", "generic_verified")
            logger.info("    Contact: %s <%s> [%s]",
                        contact.get("name") or "—", contact_email or "none", contact.get("source"))
            if email_ready and contact_email and "@" in contact_email and reliable:
                if simulate:
                    outreach_status = "simulated"
                    logger.info("    [SIMULATE] would email %s", contact_email)
                else:
                    try:
                        subject, body = send.compose_email(
                            job, contact, enrichment["cover_letter"], candidate, email_config
                        )
                        attachments = []
                        if resume_path:
                            attachments.append((resume_path, os.path.basename(resume_path)))
                        if cover_path:
                            attachments.append((cover_path, os.path.basename(cover_path)))
                        send.send_email(
                            email_config, contact_email, subject, body,
                            attachment_path=resume_path,
                            attachment_name=os.path.basename(resume_path) if resume_path else None,
                        )
                        outreach_status = "sent"
                        outreach_count += 1
                        logger.info("    Outreach: sent to %s", contact_email)
                    except Exception as exc:  # noqa: BLE001
                        outreach_status = "failed"
                        logger.warning("    Outreach failed: %s", exc)
            else:
                logger.info("    Outreach: skipped (no reliable contact email)")

            # 7. Log
            db.insert_application(
                job_id=job.get("id"),
                title=job.get("title", ""),
                company=job.get("company", ""),
                contact_name=contact.get("name", ""),
                contact_email=contact_email,
                contact_source=contact.get("source", ""),
                resume_text=enrichment["resume"],
                cover_letter=enrichment["cover_letter"],
                resume_mode=resume_mode,
                style_variant=enrichment.get("style_variant", ""),
                apply_method=apply_method,
                apply_status=apply_status,
                outreach_status=outreach_status,
                error=apply_error,
                profile_id=pid,
            )
            # Simulated jobs stay re-runnable; live applies are marked done.
            db.mark_job_status(job.get("id"), "simulated" if simulate else "applied")

        except Exception as exc:  # noqa: BLE001 — isolate per-job failures
            logger.error("    Job failed: %s", exc)
            try:
                db.insert_application(
                    job_id=job.get("id"),
                    title=job.get("title", ""),
                    company=job.get("company", ""),
                    contact_name="",
                    contact_email="",
                    contact_source="",
                    resume_text="",
                    cover_letter="",
                    resume_mode=resume_mode,
                    apply_status="error",
                    outreach_status="skipped",
                    error=str(exc),
                    profile_id=pid,
                )
                db.mark_job_status(job.get("id"), "error")
            except Exception:  # noqa: BLE001
                pass

    logger.info("=" * 60)
    logger.info(
        "PIPELINE COMPLETE — Profile %d: %d/%d applied, %d outreach emails",
        pid, applied_count, len(selected), outreach_count,
    )
    logger.info("=" * 60)


def _run_all_profiles():
    """Run pipeline for all active profiles. Used by scheduler."""
    profiles = db.get_profiles()
    for profile in profiles:
        try:
            run_daily_pipeline(profile_id=profile["id"], simulate=False)
        except Exception as exc:
            logger.error("Profile %s (%d) failed: %s", profile["name"], profile["id"], exc)
            continue


def _load_role_template(template_name: str) -> dict:
    """Load a role template YAML file. Returns empty dict if not found."""
    template_path = os.path.join(TEMPLATES_DIR, f"{template_name}.yaml")
    if not os.path.exists(template_path):
        return {}
    try:
        import yaml
        with open(template_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    db.init_db()

    # Set access code from environment variable if not already in DB
    env_code = os.environ.get("ACCESS_CODE")
    if env_code and not db.get_setting("access_code"):
        db.set_setting("access_code", env_code)
        logger.info("Access code set from environment variable")

    schedule_hour = db.get_setting("schedule_hour", 8)
    schedule_minute = db.get_setting("schedule_minute", 0)

    scheduler.add_job(
        _run_all_profiles,
        "cron",
        hour=schedule_hour,
        minute=schedule_minute,
        id="daily_pipeline",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — daily at %02d:%02d", schedule_hour, schedule_minute)

    yield

    scheduler.shutdown()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Job Hunter", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class SettingsUpdate(BaseModel):
    profile_id: Optional[int] = None
    candidate: Optional[dict] = None
    search: Optional[dict] = None
    llm: Optional[dict] = None
    email: Optional[dict] = None
    platform_credentials: Optional[dict] = None
    resume_mode: Optional[str] = None
    base_resume: Optional[str] = None
    base_cover_letter: Optional[str] = None
    schedule_hour: Optional[int] = None
    schedule_minute: Optional[int] = None


class ManualRunRequest(BaseModel):
    profile_id: Optional[int] = None
    dry_run: bool = False   # scrape + select only
    simulate: bool = False  # full flow, but apply/email nothing


class ProfileCreate(BaseModel):
    name: str
    role_template: str = "general"


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    role_template: Optional[str] = None
    is_active: Optional[bool] = None


class AuthRequest(BaseModel):
    access_code: str


class AccessCodeSet(BaseModel):
    access_code: str


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.post("/api/auth/verify")
def verify_auth(req: AuthRequest):
    """Verify access code and return session token."""
    if _verify_access_code(req.access_code):
        token = _create_session(1)
        return {"status": "ok", "token": token, "expires_in": SESSION_TTL}
    raise HTTPException(status_code=401, detail="Invalid access code")


@app.get("/api/auth/status")
def auth_status():
    """Check if access code protection is enabled."""
    return {"required": _check_access_code_enabled()}


@app.post("/api/auth/access-code")
def set_access_code(req: AccessCodeSet, request: Request):
    """Set or update the access code. Requires valid session if already set."""
    if _check_access_code_enabled():
        # Must be authenticated to change
        _validate_session(request)
    db.set_setting("access_code", req.access_code)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Profile routes
# ---------------------------------------------------------------------------
@app.get("/api/profiles")
def list_profiles(request: Request):
    """List all active profiles."""
    _validate_session(request)
    return db.get_profiles()


@app.post("/api/profiles")
def create_profile(req: ProfileCreate, request: Request):
    """Create a new profile."""
    _validate_session(request)
    profile_id = db.create_profile(req.name, req.role_template)
    return {"status": "ok", "id": profile_id}


@app.put("/api/profiles/{profile_id}")
def update_profile(profile_id: int, req: ProfileUpdate, request: Request):
    """Update a profile."""
    _validate_session(request)
    db.update_profile(profile_id, name=req.name, role_template=req.role_template, is_active=req.is_active)
    return {"status": "ok"}


@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: int, request: Request):
    """Soft-delete a profile."""
    _validate_session(request)
    db.delete_profile(profile_id)
    return {"status": "ok"}


@app.get("/api/profiles/{profile_id}/settings")
def get_profile_settings(profile_id: int, request: Request):
    """Get all settings for a specific profile."""
    _validate_session(request)
    settings = db.get_all_profile_settings(profile_id)
    # Mask sensitive fields
    _mask_settings(settings)
    return settings


@app.put("/api/profiles/{profile_id}/settings")
def update_profile_settings(profile_id: int, updates: SettingsUpdate, request: Request):
    """Update settings for a specific profile."""
    _validate_session(request)
    data = updates.model_dump(exclude_none=True)
    data.pop("profile_id", None)  # Don't store profile_id as a setting
    _merge_and_save_settings(profile_id, data)
    return {"status": "ok", "updated": list(data.keys())}


@app.get("/api/templates")
def list_templates(request: Request):
    """List available role templates."""
    _validate_session(request)
    templates = []
    if os.path.isdir(TEMPLATES_DIR):
        for fname in sorted(os.listdir(TEMPLATES_DIR)):
            if fname.endswith(".yaml") or fname.endswith(".yml"):
                name = fname.rsplit(".", 1)[0]
                template = _load_role_template(name)
                templates.append({
                    "id": name,
                    "name": template.get("name", name),
                    "default_job_titles": template.get("default_job_titles", []),
                })
    return templates


# ---------------------------------------------------------------------------
# Settings routes (backward-compatible — uses profile_id or defaults to 1)
# ---------------------------------------------------------------------------
@app.get("/api/settings")
def get_settings(request: Request, profile_id: int = 1):
    _validate_session(request)
    settings = db.get_all_settings(profile_id=profile_id)
    _mask_settings(settings)
    return settings


@app.put("/api/settings")
def update_settings(updates: SettingsUpdate, request: Request):
    pid = updates.profile_id or 1
    _validate_session(request)
    data = updates.model_dump(exclude_none=True)
    data.pop("profile_id", None)
    _merge_and_save_settings(pid, data)
    return {"status": "ok", "updated": list(data.keys())}


def _mask_settings(settings: dict):
    """Mask sensitive fields in settings dict."""
    if isinstance(settings.get("llm"), dict) and settings["llm"].get("api_key"):
        key = settings["llm"]["api_key"]
        settings["llm"]["api_key_masked"] = key[:8] + "..." if len(key) > 8 else "***"
        settings["llm"].pop("api_key", None)
    if isinstance(settings.get("email"), dict) and settings["email"].get("password"):
        settings["email"]["password_masked"] = "***"
        settings["email"].pop("password", None)
    if isinstance(settings.get("platform_credentials"), dict):
        for info in settings["platform_credentials"].values():
            if isinstance(info, dict) and info.get("password"):
                info["password_set"] = True
                info.pop("password", None)


def _merge_and_save_settings(profile_id: int, data: dict):
    """Merge platform_credentials and save all settings for a profile."""
    if "platform_credentials" in data:
        existing = db.get_profile_setting(profile_id, "platform_credentials", {}) or {}
        merged = dict(existing)
        for platform, info in data["platform_credentials"].items():
            base = dict(existing.get(platform, {}))
            base.update({k: v for k, v in info.items() if v != "" or k != "password"})
            if not info.get("password") and existing.get(platform, {}).get("password"):
                base["password"] = existing[platform]["password"]
            merged[platform] = base
        data["platform_credentials"] = merged

    for key, value in data.items():
        db.set_profile_setting(profile_id, key, value)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
@app.get("/api/jobs")
def list_jobs(request: Request, limit: int = 50, profile_id: int = 1):
    _validate_session(request)
    return db.get_all_jobs(limit, profile_id=profile_id)


@app.get("/api/jobs/new")
def list_new_jobs(request: Request, profile_id: int = 1):
    _validate_session(request)
    return db.get_new_jobs(100, profile_id=profile_id)


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
@app.get("/api/applications")
def list_applications(request: Request, limit: int = 100, profile_id: int = 1):
    _validate_session(request)
    return db.get_application_history(limit, profile_id=profile_id)


@app.get("/api/applications/stats")
def application_stats(request: Request, profile_id: int = 1):
    _validate_session(request)
    return db.get_application_stats(profile_id=profile_id)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
@app.post("/api/pipeline/run")
def trigger_pipeline(req: ManualRunRequest = ManualRunRequest(), request: Request = None):
    """
    Manually trigger the pipeline.
    - dry_run: scrape + select only.
    - simulate: full flow (enrich, contact, PDF) but apply/email nothing.
    - otherwise: a real run that submits applications and sends outreach.
    """
    if request:
        _validate_session(request)
    pid = req.profile_id or 1

    if req.simulate:
        try:
            run_daily_pipeline(profile_id=pid, simulate=True)
            return {"status": "simulated", "profile_id": pid}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    if req.dry_run:
        settings = db.get_all_settings(profile_id=pid)
        search_config = settings.get("search", {})
        try:
            raw_jobs = scrape.scrape_jobs(search_config)
            for job in raw_jobs:
                job["relevance_score"] = scrape.score_job(
                    job, search_config.get("job_titles", []), search_config.get("min_salary", 0)
                )
            new_count = db.insert_jobs(raw_jobs, profile_id=pid)
            selected = db.get_new_jobs(search_config.get("jobs_per_day", 10), profile_id=pid)
            return {
                "status": "dry_run",
                "profile_id": pid,
                "scraped": len(raw_jobs),
                "new": new_count,
                "selected": len(selected),
                "jobs": selected,
            }
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    try:
        run_daily_pipeline(profile_id=pid)
        return {"status": "completed", "profile_id": pid}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/pipeline/scrape")
def trigger_scrape(request: Request, profile_id: int = 1):
    """Just scrape — no applying."""
    _validate_session(request)
    settings = db.get_all_settings(profile_id=profile_id)
    search_config = settings.get("search", {})
    try:
        raw_jobs = scrape.scrape_jobs(search_config)
        for job in raw_jobs:
            job["relevance_score"] = scrape.score_job(
                job, search_config.get("job_titles", []), search_config.get("min_salary", 0)
            )
        new_count = db.insert_jobs(raw_jobs, profile_id=profile_id)
        return {"scraped": len(raw_jobs), "new": new_count, "profile_id": profile_id}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
@app.get("/api/schedule")
def get_schedule(request: Request, profile_id: int = 1):
    _validate_session(request)
    job = scheduler.get_job("daily_pipeline")
    if job:
        return {
            "enabled": True,
            "next_run": str(job.next_run_time),
            "hour": db.get_setting("schedule_hour", 8),
            "minute": db.get_setting("schedule_minute", 0),
        }
    return {"enabled": False}


@app.put("/api/schedule")
def update_schedule(request: Request, hour: int = 8, minute: int = 0):
    _validate_session(request)
    db.set_setting("schedule_hour", hour)
    db.set_setting("schedule_minute", minute)
    scheduler.reschedule_job("daily_pipeline", trigger="cron", hour=hour, minute=minute)
    return {"status": "ok", "hour": hour, "minute": minute}


# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------
@app.get("/api/platforms")
def list_platforms(request: Request):
    """Return available job platforms (and whether each needs login credentials)."""
    _validate_session(request)
    platforms = scrape.get_available_platforms()
    for p in platforms:
        p["needs_login"] = p["id"] in LOGIN_PLATFORMS
    return platforms


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat(), "version": "2.0.0"}


@app.get("/")
def root():
    frontend_index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(frontend_index):
        from fastapi.responses import FileResponse
        return FileResponse(frontend_index)
    return {"message": "Job Hunter API", "docs": "/docs"}