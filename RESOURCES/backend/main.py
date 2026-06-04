"""
Job Hunter — FastAPI web app with built-in scheduler.

Runs the daily job application pipeline on a schedule.
Provides a REST API for the frontend dashboard.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database as db
from pipeline import scrape, contacts, customize, send

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobhunter")

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
scheduler = BackgroundScheduler()


def run_daily_pipeline():
    """The daily pipeline — runs at scheduled time."""
    logger.info("=" * 60)
    logger.info("DAILY PIPELINE STARTED — %s", datetime.now().isoformat())
    logger.info("=" * 60)

    settings = db.get_all_settings()
    if not settings.get("candidate", {}).get("name"):
        logger.warning("Pipeline skipped — candidate not configured")
        return

    candidate = settings.get("candidate", {})
    search_config = settings.get("search", {})
    llm_config = settings.get("llm", {})
    email_config = settings.get("email", {})
    base_resume = settings.get("base_resume", "")
    base_cover = settings.get("base_cover_letter", "")

    # Step 1: Scrape
    logger.info("Step 1/5: Scraping job boards...")
    try:
        raw_jobs = scrape.scrape_jobs(search_config)
        for job in raw_jobs:
            job["relevance_score"] = scrape.score_job(
                job, search_config.get("job_titles", []), search_config.get("min_salary", 0)
            )
        new_count = db.insert_jobs(raw_jobs)
        logger.info("  Scraped %d jobs, %d new", len(raw_jobs), new_count)
    except Exception as e:
        logger.error("  Scrape failed: %s", e)
        return

    # Step 2: Select top 10
    logger.info("Step 2/5: Selecting top jobs...")
    jobs_per_day = search_config.get("jobs_per_day", 10)
    selected = db.get_new_jobs(jobs_per_day)
    logger.info("  Selected %d jobs", len(selected))

    if not selected:
        logger.info("  No new jobs. Pipeline done.")
        return

    # Step 3-5: For each job: find contact, customize, send
    sent_count = 0
    for job in selected:
        title = job.get("title", "?")[:40]
        company = job.get("company", "?")
        logger.info("  Processing: %s at %s", title, company)

        # 3. Find contact
        contact = contacts.find_contact(job)
        logger.info("    Contact: %s (%s)", contact["name"], contact["email"])

        # 4. Customize resume + cover letter
        custom_resume = customize.customize_resume(llm_config, job, base_resume, candidate)
        if not custom_resume:
            custom_resume = base_resume

        custom_cover = customize.customize_cover_letter(
            llm_config, job, base_resume, base_cover, candidate
        )
        if not custom_cover:
            custom_cover = f"I am writing to express my interest in the {title} position at {company}."

        # 5. Send email
        to_email = contact.get("email", "")
        if to_email and "@" in to_email:
            subject, body = send.compose_email(job, contact, custom_cover, candidate, email_config)
            try:
                send.send_email(email_config, to_email, subject, body)
                status = "sent"
                error = None
                sent_count += 1
                logger.info("    ✓ Sent to %s", to_email)
            except Exception as e:
                status = "failed"
                error = str(e)
                logger.error("    ✗ Send failed: %s", e)
        else:
            status = "skipped"
            error = "No valid email"
            logger.info("    ⚠ Skipped — no email")

        # Log application
        db.insert_application(
            job_id=job["id"],
            title=job.get("title", ""),
            company=job.get("company", ""),
            contact_name=contact.get("name", ""),
            contact_email=contact.get("email", ""),
            contact_source=contact.get("source", ""),
            resume_text=custom_resume,
            cover_letter=custom_cover,
        )
        db.mark_job_status(job["id"], "applied")

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE — %d/%d sent", sent_count, len(selected))
    logger.info("=" * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    db.init_db()

    # Load schedule from settings or default to 8:00 AM
    schedule_hour = db.get_setting("schedule_hour", 8)
    schedule_minute = db.get_setting("schedule_minute", 0)

    scheduler.add_job(
        run_daily_pipeline,
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
app = FastAPI(title="Job Hunter", version="1.0.0", lifespan=lifespan)

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
    candidate: dict | None = None
    search: dict | None = None
    llm: dict | None = None
    email: dict | None = None
    base_resume: str | None = None
    base_cover_letter: str | None = None
    schedule_hour: int | None = None
    schedule_minute: int | None = None


class ManualRunRequest(BaseModel):
    dry_run: bool = False


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

# --- Settings ---
@app.get("/api/settings")
def get_settings():
    settings = db.get_all_settings()
    # Mask sensitive fields
    if "llm" in settings and settings["llm"].get("api_key"):
        key = settings["llm"]["api_key"]
        settings["llm"]["api_key_masked"] = key[:8] + "..." if len(key) > 8 else "***"
    if "email" in settings and settings["email"].get("password"):
        settings["email"]["password_masked"] = "***"
    return settings


@app.put("/api/settings")
def update_settings(updates: SettingsUpdate):
    data = updates.model_dump(exclude_none=True)
    for key, value in data.items():
        db.set_setting(key, value)
    return {"status": "ok", "updated": list(data.keys())}


# --- Jobs ---
@app.get("/api/jobs")
def list_jobs(limit: int = 50):
    return db.get_all_jobs(limit)


@app.get("/api/jobs/new")
def list_new_jobs():
    return db.get_new_jobs(100)


# --- Applications ---
@app.get("/api/applications")
def list_applications(limit: int = 100):
    return db.get_application_history(limit)


@app.get("/api/applications/stats")
def application_stats():
    return db.get_application_stats()


# --- Pipeline ---
@app.post("/api/pipeline/run")
def trigger_pipeline(req: ManualRunRequest = ManualRunRequest()):
    """Manually trigger the pipeline."""
    if req.dry_run:
        # Just scrape and select, don't send
        settings = db.get_all_settings()
        search_config = settings.get("search", {})
        try:
            raw_jobs = scrape.scrape_jobs(search_config)
            for job in raw_jobs:
                job["relevance_score"] = scrape.score_job(
                    job, search_config.get("job_titles", []), search_config.get("min_salary", 0)
                )
            new_count = db.insert_jobs(raw_jobs)
            selected = db.get_new_jobs(search_config.get("jobs_per_day", 10))
            return {
                "status": "dry_run",
                "scraped": len(raw_jobs),
                "new": new_count,
                "selected": len(selected),
                "jobs": selected,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        try:
            run_daily_pipeline()
            return {"status": "completed"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/scrape")
def trigger_scrape():
    """Just scrape — no sending."""
    settings = db.get_all_settings()
    search_config = settings.get("search", {})
    try:
        raw_jobs = scrape.scrape_jobs(search_config)
        for job in raw_jobs:
            job["relevance_score"] = scrape.score_job(
                job, search_config.get("job_titles", []), search_config.get("min_salary", 0)
            )
        new_count = db.insert_jobs(raw_jobs)
        return {"scraped": len(raw_jobs), "new": new_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Scheduler ---
@app.get("/api/schedule")
def get_schedule():
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
def update_schedule(hour: int = 8, minute: int = 0):
    db.set_setting("schedule_hour", hour)
    db.set_setting("schedule_minute", minute)
    scheduler.reschedule_job("daily_pipeline", trigger="cron", hour=hour, minute=minute)
    return {"status": "ok", "hour": hour, "minute": minute}


# --- Health ---
@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


# --- Platforms ---
@app.get("/api/platforms")
def list_platforms():
    """Return available job platforms."""
    from pipeline.scrape import get_available_platforms
    return get_available_platforms()


@app.get("/")
def root():
    frontend_index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(frontend_index):
        from fastapi.responses import FileResponse
        return FileResponse(frontend_index)
    return {"message": "Job Hunter API", "docs": "/docs"}
