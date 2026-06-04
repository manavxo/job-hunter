"""
Platform applier — submit applications through job boards.

Two flows:
1. Platform apply (LinkedIn, Indeed, Glassdoor) — browser automation via Playwright
2. Direct contact (Craigslist, generic) — extract email/phone from post, reach out directly

Usage:
    from pipeline.applier import apply_to_job
"""

import os
import re
import time
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger("jobhunter.applier")


def get_platform(job_url):
    """Detect which platform the job is on."""
    if not job_url:
        return "unknown"
    url = job_url.lower()
    if "linkedin.com" in url:
        return "linkedin"
    if "indeed.com" in url:
        return "indeed"
    if "glassdoor.com" in url:
        return "glassdoor"
    if "craigslist.org" in url:
        return "craigslist"
    return "external"


def apply_to_job(job, credentials, candidate, email_config, resume_path=None, cover_letter=None):
    """
    Apply to a job. Routes to the right method based on platform.

    Args:
        job: dict with job_url, title, company, description, etc.
        credentials: dict with platform credentials
        candidate: dict with name, email, phone, location, linkedin
        email_config: dict with SMTP settings
        resume_path: optional path to resume PDF
        cover_letter: optional cover letter text

    Returns:
        dict with {status, method, error}
    """
    platform = get_platform(job.get("job_url", ""))
    job_url = job.get("job_url", "")

    if not job_url:
        return {"status": "skipped", "method": "none", "error": "No job URL"}

    # Route to the right handler
    if platform == "linkedin":
        return _apply_linkedin(job, credentials, candidate, resume_path)
    elif platform == "indeed":
        return _apply_indeed(job, credentials, candidate, resume_path)
    elif platform == "craigslist":
        return _apply_craigslist(job, candidate, email_config, resume_path, cover_letter)
    elif platform in ("glassdoor", "external"):
        return _apply_external(job, credentials, candidate, resume_path, email_config, cover_letter)
    else:
        return {"status": "skipped", "method": "unknown", "error": f"Unknown platform: {platform}"}


# ---------------------------------------------------------------------------
# Craigslist — direct contact (email, phone, text)
# ---------------------------------------------------------------------------
def _apply_craigslist(job, candidate, email_config, resume_path, cover_letter):
    """
    Craigslist jobs don't have application portals.
    The post contains contact info: email, phone, or instructions.

    Flow:
    1. Extract email addresses from the post
    2. Extract phone numbers from the post
    3. If email found → send personalized email with resume
    4. If phone found → log it (can't auto-call), send SMS if possible
    5. If neither → log for manual follow-up
    """
    description = job.get("description", "")
    title = job.get("title", "")
    company = job.get("company", "Craigslist Posting")

    # Extract emails from description
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', description)
    emails = [e for e in emails if not any(skip in e.lower() for skip in [
        "noreply", "no-reply", "donotreply", "example.com", "test.com"
    ])]

    # Extract phone numbers from description
    phones = re.findall(
        r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        description
    )
    # Clean phone numbers
    phones = [re.sub(r'[^\d+]', '', p) for p in phones]
    phones = [p for p in phones if len(p) >= 10]

    # Check for "text" or "call" instructions
    wants_text = bool(re.search(r'\b(text|txt|sms)\b', description.lower()))
    wants_call = bool(re.search(r'\b(call|phone|ring)\b', description.lower()))
    wants_email = bool(re.search(r'\b(email|e-mail|send)\b', description.lower()))

    results = []

    # If email found → send email
    if emails:
        to_email = emails[0]
        logger.info("    Craigslist: found email %s", to_email)

        subject = f"Application: {title} — {candidate.get('name', '')}"
        body = _compose_craigslist_email(job, candidate, cover_letter)

        try:
            _send_email(email_config, to_email, subject, body, resume_path)
            results.append({"status": "applied", "method": "email", "contact": to_email})
            logger.info("    ✓ Email sent to %s", to_email)
        except Exception as e:
            results.append({"status": "failed", "method": "email", "contact": to_email, "error": str(e)})
            logger.error("    ✗ Email failed: %s", e)

    # If phone found → log for manual follow-up or SMS
    if phones:
        for phone in phones[:2]:  # Max 2 numbers
            logger.info("    Craigslist: found phone %s", phone)
            results.append({
                "status": "phone_found",
                "method": "sms" if wants_text else "call",
                "contact": phone,
                "note": "Needs manual follow-up" if wants_call else "SMS candidate",
            })

    # No contact found
    if not results:
        # Try the Craigslist reply email (anonymized @sale.craigslist.org)
        reply_link = re.findall(r'mailto:([^\s"]+)', description)
        if reply_link:
            try:
                _send_email(email_config, reply_link[0], 
                           f"Application: {title}", 
                           _compose_craigslist_email(job, candidate, cover_letter),
                           resume_path)
                results.append({"status": "applied", "method": "email", "contact": reply_link[0]})
            except Exception as e:
                results.append({"status": "failed", "method": "email", "error": str(e)})
        else:
            results.append({
                "status": "no_contact",
                "method": "manual",
                "error": "No email or phone found in Craigslist post — needs manual review",
            })

    # Return the best result
    applied = [r for r in results if r["status"] == "applied"]
    if applied:
        return applied[0]
    return results[0] if results else {"status": "skipped", "method": "none", "error": "No contact info"}


def _compose_craigslist_email(job, candidate, cover_letter):
    """Compose a Craigslist-specific email. More casual than formal."""
    title = job.get("title", "the position")
    name = candidate.get("name", "")
    phone = candidate.get("phone", "")
    linkedin = candidate.get("linkedin", "")

    # Use cover letter if available, otherwise a shorter CL-specific version
    if cover_letter and len(cover_letter) > 50:
        body = cover_letter
    else:
        body = f"""Hi,

I saw your Craigslist post for {title} and wanted to reach out.

I have experience in project management and would love to discuss this opportunity.

My resume is attached. Feel free to call or text me anytime.

Best,
{name}
{phone}
{linkedin}
"""

    body += f"\n\n---\n{name}\n{phone}"
    if linkedin:
        body += f"\n{linkedin}"

    return body


# ---------------------------------------------------------------------------
# LinkedIn — browser automation
# ---------------------------------------------------------------------------
def _apply_linkedin(job, credentials, candidate, resume_path):
    """Apply via LinkedIn Easy Apply."""
    email = credentials.get("linkedin_email", "")
    password = credentials.get("linkedin_password", "")

    if not email or not password:
        return {"status": "skipped", "method": "linkedin", "error": "LinkedIn credentials not set"}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"status": "error", "method": "linkedin", "error": "playwright not installed"}

    job_url = job.get("job_url", "")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()

            # Login
            logger.info("    Logging into LinkedIn...")
            page.goto("https://www.linkedin.com/login")
            page.fill('input#username', email)
            page.fill('input#password', password)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")

            # Security check
            if "checkpoint" in page.url or "challenge" in page.url:
                browser.close()
                return {"status": "blocked", "method": "linkedin", "error": "Security challenge — needs manual login"}

            # Navigate to job
            page.goto(job_url)
            page.wait_for_load_state("networkidle")

            # Try Easy Apply
            easy_apply = page.locator('button:has-text("Easy Apply")')
            if easy_apply.count() > 0:
                easy_apply.first.click()
                page.wait_for_timeout(2000)

                # Fill form steps
                for step in range(5):
                    _fill_linkedin_form(page, candidate, resume_path)
                    submit = page.locator('button:has-text("Submit")')
                    next_btn = page.locator('button:has-text("Next")')
                    if submit.count() > 0:
                        submit.first.click()
                        page.wait_for_timeout(2000)
                        browser.close()
                        return {"status": "applied", "method": "linkedin_easy_apply", "error": None}
                    elif next_btn.count() > 0:
                        next_btn.first.click()
                        page.wait_for_timeout(1500)
                    else:
                        break

                browser.close()
                return {"status": "partial", "method": "linkedin_easy_apply", "error": "Could not complete form"}
            else:
                browser.close()
                return {"status": "redirected", "method": "linkedin_external", "error": "No Easy Apply — uses external site"}

    except Exception as e:
        return {"status": "error", "method": "linkedin", "error": str(e)}


# ---------------------------------------------------------------------------
# Indeed — browser automation
# ---------------------------------------------------------------------------
def _apply_indeed(job, credentials, candidate, resume_path):
    """Apply via Indeed."""
    email = credentials.get("indeed_email", "")
    password = credentials.get("indeed_password", "")

    if not email or not password:
        return {"status": "skipped", "method": "indeed", "error": "Indeed credentials not set"}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"status": "error", "method": "indeed", "error": "playwright not installed"}

    job_url = job.get("job_url", "")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()

            # Login
            logger.info("    Logging into Indeed...")
            page.goto("https://secure.indeed.com/auth")
            page.fill('input[name="__email"]', email)
            page.click('button[type="submit"]')
            page.wait_for_timeout(2000)
            page.fill('input[name="__password"]', password)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")

            # Navigate to job
            page.goto(job_url)
            page.wait_for_load_state("networkidle")

            # Apply
            apply_btn = page.locator('button:has-text("Apply"), a:has-text("Apply")')
            if apply_btn.count() > 0:
                apply_btn.first.click()
                page.wait_for_timeout(3000)
                _fill_generic_form(page, candidate, resume_path)
                browser.close()
                return {"status": "applied", "method": "indeed", "error": None}

            browser.close()
            return {"status": "skipped", "method": "indeed", "error": "No apply button found"}

    except Exception as e:
        return {"status": "error", "method": "indeed", "error": str(e)}


# ---------------------------------------------------------------------------
# External / Glassdoor — browser automation + email fallback
# ---------------------------------------------------------------------------
def _apply_external(job, credentials, candidate, resume_path, email_config, cover_letter):
    """
    Apply on external company careers pages.
    Tries browser automation first, falls back to email if available.
    """
    job_url = job.get("job_url", "")
    description = job.get("description", "")

    # Try browser automation
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()
            page.goto(job_url)
            page.wait_for_load_state("networkidle")

            result = _fill_generic_form(page, candidate, resume_path)
            browser.close()

            if result["status"] != "skipped":
                return result

    except Exception:
        pass

    # Fallback: try to find email in description and send directly
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', description)
    emails = [e for e in emails if not any(skip in e.lower() for skip in [
        "noreply", "no-reply", "example.com"
    ])]

    if emails and email_config:
        to_email = emails[0]
        subject = f"Application: {job.get('title', '')} — {candidate.get('name', '')}"
        body = cover_letter or f"I am interested in the {job.get('title', '')} position."
        try:
            _send_email(email_config, to_email, subject, body, resume_path)
            return {"status": "applied", "method": "email_fallback", "contact": to_email}
        except Exception as e:
            return {"status": "failed", "method": "email_fallback", "error": str(e)}

    return {"status": "skipped", "method": "external", "error": "Could not apply — no form or email found"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fill_linkedin_form(page, candidate, resume_path):
    """Fill LinkedIn Easy Apply form fields."""
    _try_fill(page, 'input[id*="first-name"], input[name*="firstName"]',
              candidate.get("name", "").split()[0] if candidate.get("name") else "")
    _try_fill(page, 'input[id*="last-name"], input[name*="lastName"]',
              " ".join(candidate.get("name", "").split()[1:]) if candidate.get("name") else "")
    _try_fill(page, 'input[type="email"], input[id*="email"]', candidate.get("email", ""))
    _try_fill(page, 'input[type="tel"], input[id*="phone"]', candidate.get("phone", ""))
    _try_fill(page, 'input[id*="location"], input[name*="location"]', candidate.get("location", ""))

    if resume_path and os.path.exists(resume_path):
        file_input = page.locator('input[type="file"]')
        if file_input.count() > 0:
            file_input.first.set_input_files(resume_path)


def _fill_generic_form(page, candidate, resume_path):
    """Try to fill generic job application forms."""
    filled = 0
    field_map = {
        'input[name*="first"], input[id*="first"]': candidate.get("name", "").split()[0],
        'input[name*="last"], input[id*="last"]': " ".join(candidate.get("name", "").split()[1:]),
        'input[name*="email"], input[type="email"]': candidate.get("email", ""),
        'input[name*="phone"], input[type="tel"]': candidate.get("phone", ""),
        'input[name*="location"], input[name*="city"]': candidate.get("location", ""),
    }
    for selector, value in field_map.items():
        if value and _try_fill(page, selector, value):
            filled += 1

    if resume_path and os.path.exists(resume_path):
        file_input = page.locator('input[type="file"]')
        if file_input.count() > 0:
            try:
                file_input.first.set_input_files(resume_path)
                filled += 1
            except Exception:
                pass

    if filled > 0:
        return {"status": "partial", "method": "external_form", "error": f"Filled {filled} fields — may need manual review"}
    return {"status": "skipped", "method": "external_form", "error": "No fillable fields found"}


def _try_fill(page, selector, value):
    """Try to fill a form field."""
    try:
        el = page.locator(selector)
        if el.count() > 0 and value:
            el.first.fill(value)
            return True
    except Exception:
        pass
    return False


def _send_email(email_config, to_email, subject, body, attachment_path=None):
    """Send email via Gmail SMTP."""
    msg = MIMEMultipart()
    msg["From"] = f"{email_config['from_name']} <{email_config['from_email']}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_path)}")
            msg.attach(part)

    with smtplib.SMTP(email_config["smtp_host"], email_config["smtp_port"]) as server:
        server.starttls()
        server.login(email_config["username"], email_config["password"])
        server.send_message(msg)

    return True
