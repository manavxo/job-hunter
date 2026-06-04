"""
SQLite database for Job Hunter web app.

Tables:
- settings: Key-value config store
- jobs: Scraped jobs
- applications: Sent applications with status
"""

import json
import os
import sqlite3
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "jobhunter.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT,
            title TEXT,
            company TEXT,
            location TEXT,
            description TEXT,
            job_url TEXT,
            date_posted TEXT,
            site TEXT,
            salary_min TEXT,
            salary_max TEXT,
            relevance_score REAL DEFAULT 0,
            status TEXT DEFAULT 'new',
            scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            title TEXT,
            company TEXT,
            contact_name TEXT,
            contact_email TEXT,
            contact_source TEXT,
            resume_text TEXT,
            cover_letter TEXT,
            status TEXT DEFAULT 'pending',
            error TEXT,
            sent_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_company_title ON jobs(company, title);
        CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
def get_setting(key, default=None):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return row["value"]
    return default


def set_setting(key, value):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, json.dumps(value) if not isinstance(value, str) else value),
    )
    conn.commit()
    conn.close()


def get_all_settings():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    result = {}
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            result[row["key"]] = row["value"]
    return result


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
def insert_jobs(jobs):
    """Insert scraped jobs. Returns count of new inserts."""
    conn = get_db()
    count = 0
    for job in jobs:
        # Check for duplicate
        existing = conn.execute(
            "SELECT id FROM jobs WHERE company = ? AND title = ?",
            (job.get("company", ""), job.get("title", "")),
        ).fetchone()
        if existing:
            continue

        conn.execute(
            """INSERT INTO jobs (external_id, title, company, location, description,
               job_url, date_posted, site, salary_min, salary_max, relevance_score, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
            (
                job.get("id", ""),
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", ""),
                job.get("description", ""),
                job.get("job_url", ""),
                job.get("date_posted", ""),
                job.get("site", ""),
                job.get("salary_min", ""),
                job.get("salary_max", ""),
                job.get("relevance_score", 0),
            ),
        )
        count += 1
    conn.commit()
    conn.close()
    return count


def get_new_jobs(limit=10):
    """Get top new jobs by relevance score."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM jobs WHERE status = 'new' ORDER BY relevance_score DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_job_status(job_id, status):
    conn = get_db()
    conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    conn.commit()
    conn.close()


def get_all_jobs(limit=100):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM jobs ORDER BY scraped_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
def insert_application(job_id, title, company, contact_name, contact_email,
                       contact_source, resume_text, cover_letter):
    conn = get_db()
    conn.execute(
        """INSERT INTO applications (job_id, title, company, contact_name,
           contact_email, contact_source, resume_text, cover_letter, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (job_id, title, company, contact_name, contact_email,
         contact_source, resume_text, cover_letter),
    )
    conn.commit()
    conn.close()


def get_pending_applications():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM applications WHERE status = 'pending' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_application_sent(app_id):
    conn = get_db()
    conn.execute(
        "UPDATE applications SET status = 'sent', sent_at = ? WHERE id = ?",
        (datetime.now().isoformat(), app_id),
    )
    conn.commit()
    conn.close()


def mark_application_failed(app_id, error):
    conn = get_db()
    conn.execute(
        "UPDATE applications SET status = 'failed', error = ? WHERE id = ?",
        (error, app_id),
    )
    conn.commit()
    conn.close()


def get_application_history(limit=100):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM applications ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_application_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM applications").fetchone()["c"]
    sent = conn.execute("SELECT COUNT(*) as c FROM applications WHERE status='sent'").fetchone()["c"]
    failed = conn.execute("SELECT COUNT(*) as c FROM applications WHERE status='failed'").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) as c FROM applications WHERE status='pending'").fetchone()["c"]
    jobs_total = conn.execute("SELECT COUNT(*) as c FROM jobs").fetchone()["c"]
    conn.close()
    return {
        "total_applications": total,
        "sent": sent,
        "failed": failed,
        "pending": pending,
        "total_jobs_scraped": jobs_total,
    }
