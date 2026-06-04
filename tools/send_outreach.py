"""
Send personalized outreach emails for job applications.

Composes a tailored email for each application and sends via Gmail SMTP.
Logs every application to applications.log.

Usage:
    python tools/send_outreach.py

Input:  .tmp/applications/{id}_job.json + {id}_contact.json + {id}_cover.md + {id}_resume.md
Output: Emails sent + applications.log updated
"""

import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def compose_email(job, contact, cover_letter, resume_text, config):
    """Build a personalized outreach email."""
    candidate = config["candidate"]
    email_cfg = config["email"]

    recipient_name = contact.get("name", "Hiring Manager")
    if not recipient_name or recipient_name.strip() == "":
        recipient_name = "Hiring Manager"

    company = job.get("company", "your company")
    job_title = job.get("title", "the open position")

    # Subject line — personalized and specific
    subject = f"Application: {job_title} at {company} — {candidate['name']}"

    # Body — the cover letter is already customized by the LLM
    body = f"""Dear {recipient_name},

{cover_letter}

---
{email_cfg.get('signature', candidate['name'])}

📎 Resume attached
🔗 LinkedIn: {candidate['linkedin']}
📋 Job posting: {job.get('job_url', '')}
"""

    return subject, body


def send_email(config, to_email, subject, body, resume_path=None):
    """Send email via Gmail SMTP."""
    email_cfg = config["email"]

    msg = MIMEMultipart()
    msg["From"] = f"{email_cfg['from_name']} <{email_cfg['from_email']}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Attach resume if available
    if resume_path and os.path.exists(resume_path):
        with open(resume_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            filename = os.path.basename(resume_path)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)

    # Send
    with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"]) as server:
        server.starttls()
        server.login(email_cfg["username"], email_cfg["password"])
        server.send_message(msg)

    return True


def log_application(config, job, contact, status, error=None):
    """Append application record to log file."""
    log_path = os.path.join(PROJECT_DIR, config["paths"]["applications_log"])
    entry = {
        "timestamp": datetime.now().isoformat(),
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "url": job.get("job_url", ""),
        "contact_name": contact.get("name", ""),
        "contact_email": contact.get("email", ""),
        "contact_source": contact.get("source", ""),
        "status": status,
        "error": error,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def main():
    config = load_config()
    tmp_dir = os.path.join(PROJECT_DIR, config["paths"]["tmp_dir"])
    apps_dir = os.path.join(tmp_dir, "applications")

    if not os.path.isdir(apps_dir):
        print("ERROR: No applications directory. Run the full pipeline first.")
        sys.exit(1)

    # Find all application files
    job_files = sorted([f for f in os.listdir(apps_dir) if f.endswith("_job.json")])

    if not job_files:
        print("No applications to send.")
        return

    print(f"\n  Sending {len(job_files)} applications...\n")

    sent = 0
    failed = 0

    for jf in job_files:
        job_id = jf.replace("_job.json", "")
        job_path = os.path.join(apps_dir, jf)
        contact_path = os.path.join(apps_dir, f"{job_id}_contact.json")
        cover_path = os.path.join(apps_dir, f"{job_id}_cover.md")
        resume_path = os.path.join(apps_dir, f"{job_id}_resume.md")

        # Load files
        with open(job_path, "r", encoding="utf-8") as f:
            job = json.load(f)

        with open(contact_path, "r", encoding="utf-8") as f:
            contact = json.load(f)

        # Read cover letter (LLM-generated)
        cover_letter = ""
        if os.path.exists(cover_path):
            with open(cover_path, "r", encoding="utf-8") as f:
                cover_letter = f.read().strip()
        else:
            print(f"  ⚠ [{job_id}] No cover letter found — skipping")
            log_application(config, job, contact, "skipped_no_cover")
            failed += 1
            continue

        # Read resume
        resume_text = ""
        if os.path.exists(resume_path):
            with open(resume_path, "r", encoding="utf-8") as f:
                resume_text = f.read().strip()

        to_email = contact.get("email", "")
        if not to_email or "@" not in to_email:
            print(f"  ⚠ [{job_id}] No valid email for {contact.get('name', '?')} — skipping")
            log_application(config, job, contact, "skipped_no_email")
            failed += 1
            continue

        # Compose
        subject, body = compose_email(job, contact, cover_letter, resume_text, config)

        company = job.get("company", "?")
        title = job.get("title", "?")[:40]
        print(f"  [{job_id}] {title} @ {company}", end=" → ", flush=True)

        # Send
        try:
            send_email(config, to_email, subject, body, resume_path=resume_path)
            print(f"✓ Sent to {to_email}")
            log_application(config, job, contact, "sent")
            sent += 1
        except Exception as e:
            print(f"✗ Failed: {e}")
            log_application(config, job, contact, "failed", error=str(e))
            failed += 1

        # Small delay between sends to avoid rate limiting
        if job_id != job_files[-1].replace("_job.json", ""):
            import time
            time.sleep(2)

    print(f"\n  {'='*50}")
    print(f"  Sent: {sent}  |  Failed: {failed}  |  Total: {len(job_files)}")


if __name__ == "__main__":
    main()
