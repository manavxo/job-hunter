"""
Email sending via Gmail SMTP.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


def send_email(email_config, to_email, subject, body, attachment_path=None, attachment_name=None):
    """
    Send an email via Gmail SMTP.

    Args:
        email_config: dict with smtp_host, smtp_port, username, password, from_name, from_email
        to_email: recipient email
        subject: email subject
        body: email body text
        attachment_path: optional file path to attach
        attachment_name: optional filename for attachment

    Returns:
        True if sent, raises on failure
    """
    msg = MIMEMultipart()
    msg["From"] = f"{email_config['from_name']} <{email_config['from_email']}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachment_path and attachment_name:
        try:
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={attachment_name}")
                msg.attach(part)
        except FileNotFoundError:
            pass

    with smtplib.SMTP(email_config["smtp_host"], email_config["smtp_port"]) as server:
        server.starttls()
        server.login(email_config["username"], email_config["password"])
        server.send_message(msg)

    return True


def compose_email(job, contact, cover_letter, candidate, email_config):
    """Build subject + body for an outreach email."""
    recipient = contact.get("name", "Hiring Manager") or "Hiring Manager"
    company = job.get("company", "your company")
    title = job.get("title", "the open position")

    subject = f"Application: {title} at {company} — {candidate.get('name', '')}"

    signature = email_config.get("signature", candidate.get("name", ""))

    body = f"""Dear {recipient},

{cover_letter}

---
{signature}

Resume attached
LinkedIn: {candidate.get('linkedin', '')}
Job posting: {job.get('job_url', '')}
"""

    return subject, body
