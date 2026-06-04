"""
Contact finder — free, no API key.

1. Extract company domain from job URL
2. Search web for hiring manager names
3. Generate email permutations
4. Verify via SMTP
"""

import re
import smtplib
import socket
import time
from urllib.parse import urlparse

import dns.resolver
import requests


def extract_domain(job):
    """Get company domain from job URL."""
    url = job.get("job_url", "")
    if url:
        try:
            host = urlparse(url).hostname or ""
            host = host.lower().replace("www.", "")
            skip = {
                "linkedin.com", "indeed.com", "glassdoor.com", "google.com",
                "ziprecruiter.com", "monster.com", "careerbuilder.com",
                "lever.co", "greenhouse.io", "workday.com", "icims.com",
                "bamboohr.com", "smartrecruiters.com", "jobvite.com",
                "myworkdayjobs.com",
            }
            if not any(s in host for s in skip):
                return host
        except Exception:
            pass

    company = job.get("company", "").strip()
    if company and company.lower() not in ("unknown", ""):
        clean = re.sub(r"[^a-zA-Z0-9\s]", "", company).strip().lower().replace(" ", "")
        if clean:
            return f"{clean}.com"
    return None


def get_mx(domain):
    try:
        records = dns.resolver.resolve(domain, "MX")
        mx = sorted(records, key=lambda r: r.preference)
        return str(mx[0].exchange).rstrip(".")
    except Exception:
        return domain


def verify_email(email, mx_host, timeout=5):
    """SMTP check — does NOT send email."""
    try:
        server = smtplib.SMTP(mx_host, 25, timeout=timeout)
        server.ehlo("verify.local")
        server.mail("check@verify.local")
        code, _ = server.rcpt(email)
        server.quit()
        return code == 250
    except Exception:
        return False


def search_names(company):
    """Search DuckDuckGo for hiring manager names."""
    names = []
    queries = [
        f'"{company}" hiring manager linkedin',
        f'"{company}" recruiter talent linkedin',
    ]
    for query in queries:
        try:
            resp = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a', resp.text, re.DOTALL)
            for snippet in snippets:
                clean = re.sub(r"<[^>]+>", " ", snippet).strip()
                match = re.search(
                    r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})\s*[\-–—]\s*(.+?)(?:\s+at\s+|\s+@\s+)",
                    clean,
                )
                if match:
                    name = match.group(1).strip()
                    title = match.group(2).strip()
                    if any(kw in title.lower() for kw in [
                        "recruit", "talent", "hiring", "hr", "manager",
                        "director", "vp", "head", "lead", "people",
                    ]):
                        names.append({"name": name, "title": title})
            time.sleep(1)
        except Exception:
            continue

    seen = set()
    unique = []
    for n in names:
        if n["name"].lower() not in seen:
            seen.add(n["name"].lower())
            unique.append(n)
    return unique[:5]


def generate_emails(first, last, domain):
    f, l = first.lower().strip(), last.lower().strip()
    fi = f[0] if f else ""
    patterns = [
        f"{f}.{l}@{domain}", f"{f}{l}@{domain}", f"{fi}.{l}@{domain}",
        f"{fi}{l}@{domain}", f"{f}_{l}@{domain}", f"{f}@{domain}",
        f"{l}.{f}@{domain}", f"{l}{f}@{domain}",
    ]
    return list(dict.fromkeys(patterns))


def extract_email_from_text(text):
    if not text:
        return None
    matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    for email in matches:
        if not any(s in email.lower() for s in ["noreply", "example.com", "test.com"]):
            return email
    return None


def find_contact(job):
    """Find best contact for a job. Returns dict."""
    company = job.get("company", "Unknown")
    description = job.get("description", "")

    result = {
        "name": "Hiring Team",
        "email": "",
        "title": "HR",
        "company": company,
        "source": "none",
    }

    # 1. Email from job description
    desc_email = extract_email_from_text(description)
    if desc_email:
        result.update({"email": desc_email, "source": "job_description"})
        return result

    # 2. Get domain
    domain = extract_domain(job)
    if not domain:
        result["email"] = f"hr@{company.lower().replace(' ', '')}.com"
        result["source"] = "fallback"
        return result

    # 3. Search for names and verify
    names = search_names(company)
    mx = get_mx(domain)

    if names and mx:
        for person in names:
            parts = person["name"].split()
            if len(parts) >= 2:
                for email in generate_emails(parts[0], parts[-1], domain):
                    if verify_email(email, mx):
                        result.update({
                            "name": person["name"],
                            "email": email,
                            "title": person["title"],
                            "source": "verified",
                        })
                        return result
                    time.sleep(0.3)

    # 4. Generic emails
    if mx:
        for prefix in ["hr", "careers", "recruiting", "jobs", "talent"]:
            email = f"{prefix}@{domain}"
            if verify_email(email, mx):
                result.update({"email": email, "source": "generic_verified"})
                return result
            time.sleep(0.3)

    # 5. Fallback
    result["email"] = f"hr@{domain}"
    result["source"] = "fallback"
    return result
