"""
Scrape job boards for fresh project management postings.

Uses the `jobspy` library to search LinkedIn, Indeed, Glassdoor,
and Google Jobs simultaneously. Filters to last 24 hours.

Usage:
    python tools/scrape_jobs.py                    # uses config.yaml defaults
    python tools/scrape_jobs.py --hours 48         # override time window
    python tools/scrape_jobs.py --titles "Senior PM,Program Manager"

Output: .tmp/today_jobs.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import yaml

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------
def scrape_jobs(config, hours=24, extra_titles=None):
    """Scrape job boards using jobspy library."""
    try:
        from jobspy import scrape_jobs as jobspy_scrape
    except ImportError:
        print("ERROR: jobspy not installed. Run: pip install python-jobspy")
        sys.exit(1)

    search_titles = extra_titles or config["search"]["job_titles"]
    locations = config["search"]["locations"]
    all_results = []

    for title in search_titles:
        for location in locations:
            print(f"  Searching: '{title}' in '{location}'...", end=" ", flush=True)
            try:
                jobs = jobspy_scrape(
                    site_name=["linkedin", "indeed", "glassdoor", "google"],
                    search_term=title,
                    location=location,
                    distance=config["search"].get("distance_miles", 25),
                    job_type="",
                    results_wanted=50,
                    hours_old=hours,
                    country_indeed="USA",
                )
                if jobs is not None and len(jobs) > 0:
                    count = len(jobs)
                    print(f"found {count}")
                    for _, row in jobs.iterrows():
                        job = {
                            "id": str(row.get("id", "")),
                            "title": str(row.get("title", "")),
                            "company": str(row.get("company", "")),
                            "location": str(row.get("location", "")),
                            "description": str(row.get("description", ""))[:3000],
                            "job_url": str(row.get("job_url", "")),
                            "date_posted": str(row.get("date_posted", "")),
                            "site": str(row.get("site", "")),
                            "salary_min": str(row.get("min_amount", "")),
                            "salary_max": str(row.get("max_amount", "")),
                            "job_type": str(row.get("job_type", "")),
                            "search_title": title,
                            "search_location": location,
                        }
                        all_results.append(job)
                else:
                    print("no results")
            except Exception as e:
                print(f"ERROR: {e}")

    return all_results


# ---------------------------------------------------------------------------
# Dedupe & filter
# ---------------------------------------------------------------------------
def dedupe_jobs(jobs):
    """Remove duplicates by (title, company) pair."""
    seen = set()
    unique = []
    for job in jobs:
        key = (job["title"].lower().strip(), job["company"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def filter_excluded(jobs, excluded_companies):
    """Remove jobs from excluded companies."""
    excluded = {c.lower() for c in excluded_companies}
    return [j for j in jobs if j["company"].lower() not in excluded]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Scrape job boards for PM roles")
    parser.add_argument("--hours", type=int, default=None, help="Hours old (default: from config)")
    parser.add_argument("--titles", type=str, default=None, help="Comma-separated extra titles")
    args = parser.parse_args()

    config = load_config()
    hours = args.hours or config["search"].get("hours_old", 24)
    extra_titles = args.titles.split(",") if args.titles else None

    print(f"\n{'='*60}")
    print(f"  JOB HUNTER — Scraping (last {hours}h)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Scrape
    jobs = scrape_jobs(config, hours=hours, extra_titles=extra_titles)
    print(f"\n  Raw results: {len(jobs)}")

    # Dedupe
    jobs = dedupe_jobs(jobs)
    print(f"  After dedup: {len(jobs)}")

    # Filter excluded companies
    excluded = config["search"].get("excluded_companies", [])
    if excluded:
        jobs = filter_excluded(jobs, excluded)
        print(f"  After exclusions: {len(jobs)}")

    # Save
    tmp_dir = os.path.join(PROJECT_DIR, config["paths"]["tmp_dir"])
    os.makedirs(tmp_dir, exist_ok=True)
    output_path = os.path.join(tmp_dir, "today_jobs.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

    print(f"\n  Saved to: {output_path}")
    print(f"  Total jobs: {len(jobs)}")
    return jobs


if __name__ == "__main__":
    main()
