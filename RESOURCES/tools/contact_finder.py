"""
Find hiring manager contacts — free, unlimited approach.

No paid APIs. Uses:
1. Domain extraction from job URL
2. Web search to find recruiter/hiring manager names
3. Email pattern generation (permutation)
4. SMTP verification (checks if email exists without sending)

Usage:
    python tools/contact_finder.py

Input:  .tmp/selected_jobs.json
Output: .tmp/applications/{id}_contact.json
"""

import json
import os
import re
import smtplib
import socket
import sys
import time
from urllib.parse import urlparse

import dns.resolver
import requests
import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# 1. Domain extraction
# ---------------------------------------------------------------------------
def extract_domain(job):
    """Get the company's email domain from the job URL or company name."""
    # Try from job URL first
    url = job.get("job_url", "")
    if url:
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            # Remove www., get base domain
            host = host.lower().replace("www.", "")
            # Skip job board domains
            skip_domains = {
                "linkedin.com", "indeed.com", "glassdoor.com", "google.com",
                "ziprecruiter.com", "monster.com", "careerbuilder.com",
                "simplyhired.com", "dice.com", "stackoverflow.com",
                "lever.co", "greenhouse.io", "workday.com", "icims.com",
                "bamboohr.com", "smartrecruiters.com", "jobvite.com",
                "myworkdayjobs.com", "wd5.myworkday.com",
            }
            for skip in skip_domains:
                if skip in host:
                    break
            else:
                # It's likely the company's own domain
                return host
        except Exception:
            pass

    # Try from company name — guess the domain
    company = job.get("company", "").strip()
    if company and company.lower() not in ("unknown", "", "confidential"):
        # Clean company name for domain guessing
        clean = re.sub(r"[^a-zA-Z0-9\s]", "", company).strip().lower().replace(" ", "")
        if clean:
            return f"{clean}.com"

    return None


def get_mx_record(domain):
    """Get the mail server for a domain."""
    try:
        records = dns.resolver.resolve(domain, "MX")
        # Sort by priority (lowest = primary)
        mx_list = sorted(records, key=lambda r: r.preference)
        return str(mx_list[0].exchange).rstrip(".")
    except Exception:
        # Fallback: try the domain itself
        return domain


# ---------------------------------------------------------------------------
# 2. Name finding via web search
# ---------------------------------------------------------------------------
def search_for_names(company, location=""):
    """Search the web for hiring manager / recruiter names at a company."""
    names = []

    queries = [
        f'"{company}" hiring manager linkedin',
        f'"{company}" recruiter talent acquisition linkedin',
        f'"{company}" HR manager linkedin',
    ]

    for query in queries:
        try:
            # Use DuckDuckGo HTML (no API key needed)
            url = "https://html.duckduckgo.com/html/"
            resp = requests.post(
                url,
                data={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=10,
            )

            if resp.status_code != 200:
                continue

            # Extract names from search results
            # Look for patterns like "John Smith - Hiring Manager at Company"
            text = resp.text
            # Find result snippets
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a', text, re.DOTALL)

            for snippet in snippets:
                # Clean HTML
                clean = re.sub(r"<[^>]+>", " ", snippet).strip()
                # Look for "Name - Title at Company" patterns
                name_match = re.search(
                    r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})\s*[\-–—]\s*(.+?)(?:\s+at\s+|\s+@\s+)",
                    clean,
                )
                if name_match:
                    name = name_match.group(1).strip()
                    title = name_match.group(2).strip()
                    if _is_relevant_title(title):
                        names.append({"name": name, "title": title})

            time.sleep(1)  # Be polite

        except Exception:
            continue

    # Dedupe by name
    seen = set()
    unique = []
    for n in names:
        key = n["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(n)

    return unique[:5]  # Top 5


def _is_relevant_title(title):
    """Check if a title suggests hiring authority."""
    title_lower = title.lower()
    keywords = [
        "recruit", "talent", "hiring", "hr ", "human resource",
        "people", "staffing", "acquisition", "vp", "director",
        "head of", "manager", "lead",
    ]
    return any(kw in title_lower for kw in keywords)


# ---------------------------------------------------------------------------
# 3. Email permutation
# ---------------------------------------------------------------------------
def generate_permutations(first_name, last_name, domain):
    """Generate common corporate email patterns."""
    f = first_name.lower().strip()
    l = last_name.lower().strip()
    fi = f[0] if f else ""
    li = l[0] if l else ""

    patterns = [
        f"{f}.{l}@{domain}",
        f"{f}{l}@{domain}",
        f"{fi}.{l}@{domain}",
        f"{fi}{l}@{domain}",
        f"{f}_{l}@{domain}",
        f"{f}@{domain}",
        f"{l}.{f}@{domain}",
        f"{l}{f}@{domain}",
        f"{f}-{l}@{domain}",
        f"{fi}_{l}@{domain}",
    ]

    return list(dict.fromkeys(patterns))  # Dedupe preserving order


def get_domain_pattern(domain):
    """Try to detect the email pattern used by a domain via Hunter.io's public endpoint."""
    try:
        resp = requests.get(
            f"https://hunter.io/domain-search?domain={domain}&type=confidence",
            timeout=5,
        )
        # This won't work without API, but it's a best-effort
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# 4. SMTP verification
# ---------------------------------------------------------------------------
def verify_email(email, mx_host, timeout=5):
    """
    Check if an email address exists by talking to the mail server.
    Does NOT send any email — just checks if the server accepts the address.
    """
    try:
        # Connect with a generic HELO
        server = smtplib.SMTP(mx_host, 25, timeout=timeout)
        server.ehlo("verify.local")
        server.mail("check@verify.local")

        code, message = server.rcpt(email)
        server.quit()

        # 250 = accepted, 550 = doesn't exist
        if code == 250:
            return True
        return False

    except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError,
            socket.timeout, ConnectionRefusedError, OSError):
        return False


def find_best_email(first_name, last_name, domain):
    """Generate permutations and verify the first one that works."""
    if not domain or not first_name or not last_name:
        return None

    mx_host = get_mx_record(domain)
    if not mx_host:
        return None

    permutations = generate_permutations(first_name, last_name, domain)

    for email in permutations:
        if verify_email(email, mx_host):
            return email
        time.sleep(0.5)  # Don't hammer the mail server

    return None


# ---------------------------------------------------------------------------
# 5. Fallback: extract email from job description
# ---------------------------------------------------------------------------
def extract_email_from_text(text):
    """Try to extract an email from job description text."""
    if not text:
        return None
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(pattern, text)
    for email in matches:
        lower = email.lower()
        if not any(skip in lower for skip in [
            "noreply", "no-reply", "donotreply", "example.com",
            "test.com", "placeholder", ".png", ".jpg",
        ]):
            return email
    return None


# ---------------------------------------------------------------------------
# 6. Main pipeline
# ---------------------------------------------------------------------------
def find_contact(job):
    """Find the best contact for a job posting."""
    company = job.get("company", "Unknown")
    location = job.get("location", "")
    description = job.get("description", "")

    result = {
        "name": "",
        "email": "",
        "title": "",
        "linkedin": "",
        "company": company,
        "source": "none",
    }

    # Step 1: Try extracting email from the job description itself
    desc_email = extract_email_from_text(description)
    if desc_email:
        result["email"] = desc_email
        result["name"] = "Hiring Team"
        result["title"] = "From job posting"
        result["source"] = "job_description"
        return result

    # Step 2: Extract domain
    domain = extract_domain(job)
    if not domain:
        result["email"] = f"hr@{company.lower().replace(' ', '')}.com"
        result["name"] = "Hiring Team"
        result["title"] = "HR"
        result["source"] = "fallback_domain"
        return result

    # Step 3: Search for names
    print(f"      Searching web for contacts...", end=" ", flush=True)
    names = search_for_names(company, location)

    if names:
        print(f"found {len(names)} names")
        # Step 4: Try to verify emails for each name
        for person in names:
            parts = person["name"].split()
            if len(parts) >= 2:
                first = parts[0]
                last = parts[-1]
                print(f"      Verifying {first}.{last}@{domain}...", end=" ", flush=True)
                email = find_best_email(first, last, domain)
                if email:
                    print(f"✓ {email}")
                    result["name"] = person["name"]
                    result["email"] = email
                    result["title"] = person["title"]
                    result["source"] = "web_search_verified"
                    return result
                else:
                    print("✗ no verified email")
    else:
        print("no names found")

    # Step 5: Try generic patterns
    generic_emails = [
        f"hr@{domain}",
        f"careers@{domain}",
        f"recruiting@{domain}",
        f"jobs@{domain}",
        f"talent@{domain}",
    ]

    mx_host = get_mx_record(domain)
    if mx_host:
        for email in generic_emails:
            print(f"      Trying {email}...", end=" ", flush=True)
            if verify_email(email, mx_host):
                print("✓")
                result["name"] = "Hiring Team"
                result["email"] = email
                result["title"] = "HR / Careers"
                result["source"] = "generic_verified"
                return result
            else:
                print("✗")
            time.sleep(0.5)

    # Step 6: Absolute fallback
    result["name"] = "Hiring Team"
    result["email"] = generic_emails[0]  # hr@domain — might bounce but it's the best we have
    result["title"] = "HR"
    result["source"] = "fallback_generic"
    return result


def main():
    config = load_config()

    # Load selected jobs
    tmp_dir = os.path.join(PROJECT_DIR, config["paths"]["tmp_dir"])
    selected_path = os.path.join(tmp_dir, "selected_jobs.json")

    if not os.path.exists(selected_path):
        print("ERROR: selected_jobs.json not found. Run select_top_10.py first.")
        sys.exit(1)

    with open(selected_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    print(f"\n{'='*60}")
    print(f"  CONTACT FINDER — {len(jobs)} jobs (free, no API key)")
    print(f"{'='*60}")

    # Create applications directory
    apps_dir = os.path.join(tmp_dir, "applications")
    os.makedirs(apps_dir, exist_ok=True)

    results = []

    for i, job in enumerate(jobs, 1):
        company = job.get("company", "Unknown")
        title = job.get("title", "")
        job_id = f"{i:03d}"

        print(f"\n  [{i}/{len(jobs)}] {title[:45]} at {company}")

        contact = find_contact(job)
        print(f"      Result: {contact['name']} — {contact['email']} (via {contact['source']})")

        # Save contact
        contact_path = os.path.join(apps_dir, f"{job_id}_contact.json")
        with open(contact_path, "w", encoding="utf-8") as f:
            json.dump(contact, f, indent=2)

        # Save job info
        job_path = os.path.join(apps_dir, f"{job_id}_job.json")
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(job, f, indent=2, ensure_ascii=False)

        results.append({"job_id": job_id, "job": job, "contact": contact})

    # Summary
    sources = {}
    for r in results:
        src = r["contact"]["source"]
        sources[src] = sources.get(src, 0) + 1

    print(f"\n  {'='*50}")
    print(f"  CONTACTS FOUND:")
    for src, count in sources.items():
        print(f"    {src}: {count}")
    print(f"  Total: {len(results)}")
    print(f"  Cost: $0")

    return results


if __name__ == "__main__":
    main()
