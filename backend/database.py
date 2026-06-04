"""
SQLite database for Job Hunter web app.

Tables:
- profiles: Multi-user profiles (each person gets their own space)
- profile_settings: Per-profile key-value config store
- settings: Global settings (access code, etc.)
- jobs: Scraped jobs (scoped per profile)
- applications: Sent applications with status (scoped per profile)
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
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist and run migrations."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role_template TEXT DEFAULT 'general',
            created_at TEXT DEFAULT (datetime('now')),
            is_active BOOLEAN DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS profile_settings (
            profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY (profile_id, key)
        );

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
            profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
            scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
            title TEXT,
            company TEXT,
            contact_name TEXT,
            contact_email TEXT,
            contact_source TEXT,
            resume_text TEXT,
            cover_letter TEXT,
            resume_mode TEXT,
            style_variant TEXT,
            apply_method TEXT,
            apply_status TEXT DEFAULT 'pending',
            outreach_status TEXT DEFAULT 'pending',
            status TEXT DEFAULT 'pending',
            error TEXT,
            sent_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_company_title ON jobs(company, title);
        CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
        CREATE INDEX IF NOT EXISTS idx_applications_apply ON applications(apply_status);
        CREATE INDEX IF NOT EXISTS idx_profile_settings_pid ON profile_settings(profile_id);
    """)

    # --- Idempotent migrations for applications table ---
    existing_app_cols = {row["name"] for row in conn.execute("PRAGMA table_info(applications)")}
    new_app_cols = {
        "resume_mode": "TEXT",
        "style_variant": "TEXT",
        "apply_method": "TEXT",
        "apply_status": "TEXT DEFAULT 'pending'",
        "outreach_status": "TEXT DEFAULT 'pending'",
        "profile_id": "INTEGER REFERENCES profiles(id) ON DELETE CASCADE",
    }
    for col, decl in new_app_cols.items():
        if col not in existing_app_cols:
            conn.execute(f"ALTER TABLE applications ADD COLUMN {col} {decl}")

    # --- Idempotent migration for jobs table ---
    existing_job_cols = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
    if "profile_id" not in existing_job_cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE")

    # --- Create indexes on profile_id columns (after migrations) ---
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_profile ON jobs(profile_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_profile ON applications(profile_id)")

    # --- Seed default profiles if none exist ---
    profile_count = conn.execute("SELECT COUNT(*) AS c FROM profiles").fetchone()["c"]
    if profile_count == 0:
        _seed_default_profiles(conn)

    # --- Migrate legacy settings to profile 1 if needed ---
    _migrate_legacy_settings(conn)

    conn.commit()
    conn.close()


def _seed_default_profiles(conn):
    """Create the three initial profiles and assign existing data to profile 1."""
    profiles = [
        (1, "My Profile", "corporate-pm"),
        (2, "Girlfriend", "healthcare"),
        (3, "Friend", "general"),
    ]
    for pid, name, template in profiles:
        conn.execute(
            "INSERT INTO profiles (id, name, role_template) VALUES (?, ?, ?)",
            (pid, name, template),
        )

    # Tag all existing untagged jobs and applications to profile 1
    conn.execute("UPDATE jobs SET profile_id = 1 WHERE profile_id IS NULL")
    conn.execute("UPDATE applications SET profile_id = 1 WHERE profile_id IS NULL")


def _migrate_legacy_settings(conn):
    """Copy flat settings into profile_settings for profile 1 if not already there."""
    legacy_rows = conn.execute("SELECT key, value FROM settings").fetchall()
    if not legacy_rows:
        return

    # Check if profile 1 already has settings
    existing = conn.execute(
        "SELECT COUNT(*) AS c FROM profile_settings WHERE profile_id = 1"
    ).fetchone()["c"]
    if existing > 0:
        return

    # Migrate all legacy settings to profile 1
    for row in legacy_rows:
        # Skip global-only settings (access_code stays in global settings)
        if row["key"] == "access_code":
            continue
        conn.execute(
            "INSERT OR IGNORE INTO profile_settings (profile_id, key, value) VALUES (?, ?, ?)",
            (1, row["key"], row["value"]),
        )


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------
def get_profiles():
    """List all profiles."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM profiles WHERE is_active = 1 ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_profile(profile_id):
    """Get a single profile by ID."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM profiles WHERE id = ?", (profile_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_profile(name, role_template="general"):
    """Create a new profile. Returns the new profile ID."""
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO profiles (name, role_template) VALUES (?, ?)",
        (name, role_template),
    )
    profile_id = cur.lastrowid
    conn.commit()
    conn.close()
    return profile_id


def update_profile(profile_id, name=None, role_template=None, is_active=None):
    """Update profile fields."""
    fields, values = [], []
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if role_template is not None:
        fields.append("role_template = ?")
        values.append(role_template)
    if is_active is not None:
        fields.append("is_active = ?")
        values.append(is_active)
    if not fields:
        return
    values.append(profile_id)
    conn = get_db()
    conn.execute(f"UPDATE profiles SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_profile(profile_id):
    """Soft-delete a profile (set is_active=0)."""
    conn = get_db()
    conn.execute("UPDATE profiles SET is_active = 0 WHERE id = ?", (profile_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Settings (global — access_code, etc.)
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


# ---------------------------------------------------------------------------
# Profile Settings (per-profile config)
# ---------------------------------------------------------------------------
def get_profile_setting(profile_id, key, default=None):
    conn = get_db()
    row = conn.execute(
        "SELECT value FROM profile_settings WHERE profile_id = ? AND key = ?",
        (profile_id, key),
    ).fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return row["value"]
    return default


def set_profile_setting(profile_id, key, value):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO profile_settings (profile_id, key, value) VALUES (?, ?, ?)",
        (profile_id, key, json.dumps(value) if not isinstance(value, str) else value),
    )
    conn.commit()
    conn.close()


def get_all_profile_settings(profile_id):
    """Get all settings for a specific profile as a nested dict."""
    conn = get_db()
    rows = conn.execute(
        "SELECT key, value FROM profile_settings WHERE profile_id = ?",
        (profile_id,),
    ).fetchall()
    conn.close()
    result = {}
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            result[row["key"]] = row["value"]
    return result


def get_all_settings(profile_id=None):
    """
    Backward-compatible settings getter.
    If profile_id is given, returns that profile's settings.
    Otherwise returns profile 1's settings (backward compat).
    """
    pid = profile_id or 1
    return get_all_profile_settings(pid)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
def insert_jobs(jobs, profile_id=None):
    """Insert scraped jobs scoped to a profile. Returns count of new inserts."""
    pid = profile_id or 1
    conn = get_db()
    count = 0
    for job in jobs:
        # Check for duplicate within the same profile
        existing = conn.execute(
            "SELECT id FROM jobs WHERE company = ? AND title = ? AND profile_id = ?",
            (job.get("company", ""), job.get("title", ""), pid),
        ).fetchone()
        if existing:
            continue

        conn.execute(
            """INSERT INTO jobs (external_id, title, company, location, description,
               job_url, date_posted, site, salary_min, salary_max, relevance_score, status, profile_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)""",
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
                pid,
            ),
        )
        count += 1
    conn.commit()
    conn.close()
    return count


def get_new_jobs(limit=10, profile_id=None):
    """Get top new jobs by relevance score, scoped to profile."""
    pid = profile_id or 1
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM jobs WHERE status = 'new' AND profile_id = ? ORDER BY relevance_score DESC LIMIT ?",
        (pid, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_job_status(job_id, status):
    conn = get_db()
    conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    conn.commit()
    conn.close()


def get_all_jobs(limit=100, profile_id=None):
    """Get all jobs, optionally scoped to a profile."""
    conn = get_db()
    if profile_id:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE profile_id = ? ORDER BY scraped_at DESC LIMIT ?",
            (profile_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY scraped_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
def insert_application(job_id, title, company, contact_name, contact_email,
                       contact_source, resume_text, cover_letter,
                       resume_mode=None, style_variant=None, apply_method=None,
                       apply_status="pending", outreach_status="pending", error=None,
                       profile_id=None):
    """Insert an application record. Returns the new row id."""
    pid = profile_id or 1
    # Overall status: 'sent' if either channel succeeded, 'failed' if both clearly failed.
    succeeded = apply_status in ("applied", "partial") or outreach_status == "sent"
    failed = (apply_status in ("failed", "error")
              and outreach_status in ("failed", "skipped", "pending"))
    status = "sent" if succeeded else ("failed" if failed else "pending")
    sent_at = datetime.now().isoformat() if succeeded else None

    conn = get_db()
    cur = conn.execute(
        """INSERT INTO applications (job_id, profile_id, title, company, contact_name,
           contact_email, contact_source, resume_text, cover_letter,
           resume_mode, style_variant, apply_method, apply_status,
           outreach_status, status, error, sent_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (job_id, pid, title, company, contact_name, contact_email,
         contact_source, resume_text, cover_letter,
         resume_mode, style_variant, apply_method, apply_status,
         outreach_status, status, error, sent_at),
    )
    app_id = cur.lastrowid
    conn.commit()
    conn.close()
    return app_id


def update_application_status(app_id, *, apply_status=None, outreach_status=None,
                              apply_method=None, error=None):
    """Update individual status fields on an application."""
    fields, values = [], []
    for col, val in (
        ("apply_status", apply_status),
        ("outreach_status", outreach_status),
        ("apply_method", apply_method),
        ("error", error),
    ):
        if val is not None:
            fields.append(f"{col} = ?")
            values.append(val)
    if not fields:
        return
    values.append(app_id)
    conn = get_db()
    conn.execute(f"UPDATE applications SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_pending_applications(profile_id=None):
    conn = get_db()
    if profile_id:
        rows = conn.execute(
            "SELECT * FROM applications WHERE status = 'pending' AND profile_id = ? ORDER BY created_at DESC",
            (profile_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM applications WHERE status = 'pending' ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_application_history(limit=100, profile_id=None):
    conn = get_db()
    if profile_id:
        rows = conn.execute(
            "SELECT * FROM applications WHERE profile_id = ? ORDER BY created_at DESC LIMIT ?",
            (profile_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM applications ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_application_stats(profile_id=None):
    """Dashboard counters across jobs and the two application channels."""
    conn = get_db()

    def count(where="", args=()):
        sql = "SELECT COUNT(*) AS c FROM applications"
        if where:
            sql += " WHERE " + where
        return conn.execute(sql, args).fetchone()["c"]

    pid_filter = ""
    pid_args = ()
    if profile_id:
        pid_filter = "profile_id = ? AND "
        pid_args = (profile_id,)

    total = count(f"{pid_filter}1=1", pid_args)
    applied = count(f"{pid_filter}apply_status IN ('applied', 'partial')", pid_args)
    outreach_sent = count(f"{pid_filter}outreach_status = 'sent'", pid_args)
    failed = count(f"{pid_filter}status = 'failed'", pid_args)
    pending = count(f"{pid_filter}status = 'pending'", pid_args)

    if profile_id:
        jobs_total = conn.execute(
            "SELECT COUNT(*) AS c FROM jobs WHERE profile_id = ?", (profile_id,)
        ).fetchone()["c"]
    else:
        jobs_total = conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"]

    conn.close()
    return {
        "total_applications": total,
        "applied": applied,
        "outreach_sent": outreach_sent,
        "failed": failed,
        "pending": pending,
        "total_jobs_scraped": jobs_total,
    }