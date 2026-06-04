"""
Look up hiring manager contacts via Apollo.io API.

For each job in selected_jobs.json:
1. Try Apollo enrichment to find the hiring manager
2. Extract their email, name, title
3. If Apollo fails or credits exhausted, try to extract email from job description
4. Fallback to company careers/HR email

Usage:
    python tools/apollo_lookup.py

Input:  .tmp/selected_jobs.json
Output: .tmp/applications/{job_id}_contact.json
"""

import json
import os
import re
import sys
import time

import requests
import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def search_apollo_people(api_key, company_name, title_keywords=None):
    """
    Search Apollo for people at a company.
    Returns the best match for a hiring manager.
    """
    url = "https://api.apollo.io/v1/mixed_people/search"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    payload = {
        "api_key": api_key,
        "q_organization_name": company_name,
        "person_titles": title_keywords or [
            "Hiring Manager",
            "Recruiter",
            "Talent Acquisition",
            "HR Manager",
            "VP",
            "Director",
        ],
        "page": 1,
        "per_page": 5,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code == 429:
            print("      ⚠ Apollo rate limited — waiting 10s...")
            time.sleep(10)
            resp = requests.post(url, json=payload, headers=headers, timeout=15)

        if resp.status_code != 200:
            print(f"      ⚠ Apollo HTTP {resp.status_code}")
            return None

        data = resp.json()
        people = data.get("people", [])

        if not people:
            return None

        # Pick best match — prefer recruiting/HR titles
        best = None
        for person in people:
            title = (person.get("title") or "").lower()
            if any(kw in title for kw in ["recruit", "talent", "hr", "hiring"]):
                best = person
                break

        if not best:
            best = people[0]

        return {
            "name": f"{best.get('first_name', '')} {best.get('last_name', '')}".strip(),
            "email": best.get("email"),
            "title": best.get("title", ""),
            "linkedin": best.get("linkedin_url", ""),
            "company": company_name,
            "source": "apollo",
        }

    except Exception as e:
        print(f"      ⚠ Apollo error: {e}")
        return None


def extract_email_from_text(text):
    """Try to extract an email from job description text."""
    if not text:
        return None
    # Look for email patterns
    patterns = [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Filter out common no-reply / generic addresses
            for email in matches:
                lower = email.lower()
                if not any(skip in lower for skip in [
                    "noreply", "no-reply", "donotreply", "example.com",
                    "test.com", "placeholder"
                ]):
                    return email
    return None


def make_fallback_contact(job):
    """Create a fallback contact from job info."""
    company = job.get("company", "Unknown")
    email = extract_email_from_text(job.get("description", ""))

    return {
        "name": "Hiring Team",
        "email": email or f"hr@{company.lower().replace(' ', '')}.com",
        "title": "Hiring Team",
        "linkedin": "",
        "company": company,
        "source": "fallback",
    }


def main():
    config = load_config()
    api_key = config["apollo"]["api_key"]

    if not api_key or api_key == "APOLLO_API_KEY_HERE":
        print("\n  ⚠ Apollo API key not configured in config.yaml")
        print("  Using fallback contacts only (no hiring manager lookup)\n")
        api_key = None

    # Load selected jobs
    tmp_dir = os.path.join(PROJECT_DIR, config["paths"]["tmp_dir"])
    selected_path = os.path.join(tmp_dir, "selected_jobs.json")

    if not os.path.exists(selected_path):
        print("ERROR: selected_jobs.json not found. Run select_top_10.py first.")
        sys.exit(1)

    with open(selected_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    print(f"\n  Looking up contacts for {len(jobs)} jobs...")

    # Create applications directory
    apps_dir = os.path.join(tmp_dir, "applications")
    os.makedirs(apps_dir, exist_ok=True)

    results = []
    apollo_credits_used = 0

    for i, job in enumerate(jobs, 1):
        company = job.get("company", "Unknown")
        title = job.get("title", "")
        job_id = f"{i:03d}"

        print(f"\n  [{i}/{len(jobs)}] {title[:40]} at {company}")

        contact = None

        # Try Apollo if key available
        if api_key:
            print("      Searching Apollo...", end=" ", flush=True)
            contact = search_apollo_people(api_key, company)
            if contact:
                apollo_credits_used += 1
                print(f"✓ Found: {contact['name']} ({contact.get('email', 'no email')})")
            else:
                print("✗ No match")

            # Small delay between Apollo calls
            if i < len(jobs):
                time.sleep(1)

        # Fallback
        if not contact:
            contact = make_fallback_contact(job)
            print(f"      Fallback: {contact['email']}")

        # Save contact
        contact_path = os.path.join(apps_dir, f"{job_id}_contact.json")
        with open(contact_path, "w", encoding="utf-8") as f:
            json.dump(contact, f, indent=2)

        # Also save the job info alongside
        job_path = os.path.join(apps_dir, f"{job_id}_job.json")
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(job, f, indent=2, ensure_ascii=False)

        results.append({"job_id": job_id, "job": job, "contact": contact})

    print(f"\n  {'='*50}")
    print(f"  Apollo credits used: {apollo_credits_used}")
    print(f"  Contacts saved to: {apps_dir}")
    return results


if __name__ == "__main__":
    main()
