"""
Select top 10 jobs from today's scrape.

Scores jobs by relevance to target titles, dedupes against past applications,
and outputs the best 10 for today's batch.

Usage:
    python tools/select_top_10.py

Input:  .tmp/today_jobs.json
Output: .tmp/selected_jobs.json
"""

import json
import os
import re
import sys
from datetime import datetime

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def load_past_applications(log_path):
    """Load set of (company, title) pairs we've already applied to."""
    applied = set()
    if not os.path.exists(log_path):
        return applied
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    key = (
                        entry.get("company", "").lower().strip(),
                        entry.get("title", "").lower().strip(),
                    )
                    applied.add(key)
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return applied


def score_job(job, target_titles, min_salary=0):
    """Score a job 0-100 based on relevance."""
    score = 0
    title = job.get("title", "").lower()
    desc = job.get("description", "").lower()

    # Title match (0-40 points)
    best_title_match = 0
    for target in target_titles:
        target_lower = target.lower()
        if target_lower in title:
            best_title_match = max(best_title_match, 40)
        elif any(word in title for word in target_lower.split()):
            best_title_match = max(best_title_match, 25)

    score += best_title_match

    # Has description (0-15 points)
    if len(desc) > 200:
        score += 15
    elif len(desc) > 50:
        score += 8

    # Has salary info (0-15 points)
    salary_min = job.get("salary_min", "")
    salary_max = job.get("salary_max", "")
    if salary_min and salary_min not in ("", "None", "0"):
        try:
            sal = float(salary_min)
            if min_salary > 0 and sal < min_salary:
                score -= 30  # Penalize below minimum
            else:
                score += 15
        except (ValueError, TypeError):
            pass

    # Has apply URL (0-10 points)
    if job.get("job_url") and job["job_url"].startswith("http"):
        score += 10

    # Has company name (0-10 points)
    if job.get("company") and len(job["company"]) > 1:
        score += 10

    # Recency bonus (0-10 points) — posted today is best
    date_posted = job.get("date_posted", "")
    if date_posted:
        try:
            posted = datetime.fromisoformat(str(date_posted).replace("Z", "+00:00"))
            hours_ago = (datetime.now(posted.tzinfo) - posted).total_seconds() / 3600
            if hours_ago < 6:
                score += 10
            elif hours_ago < 12:
                score += 7
            elif hours_ago < 24:
                score += 5
        except (ValueError, TypeError):
            pass

    return max(0, min(100, score))


def select_top_10():
    config = load_config()
    target_titles = config["search"]["job_titles"]
    jobs_per_day = config["search"].get("jobs_per_day", 10)
    min_salary = config["search"].get("min_salary", 0)

    # Load today's scraped jobs
    tmp_dir = os.path.join(PROJECT_DIR, config["paths"]["tmp_dir"])
    today_path = os.path.join(tmp_dir, "today_jobs.json")

    if not os.path.exists(today_path):
        print("ERROR: today_jobs.json not found. Run scrape_jobs.py first.")
        sys.exit(1)

    with open(today_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    print(f"\n  Loaded {len(jobs)} jobs from today's scrape")

    # Filter out already-applied
    log_path = os.path.join(PROJECT_DIR, config["paths"]["applications_log"])
    applied = load_past_applications(log_path)
    fresh_jobs = []
    skipped = 0
    for job in jobs:
        key = (job.get("company", "").lower().strip(), job.get("title", "").lower().strip())
        if key in applied:
            skipped += 1
        else:
            fresh_jobs.append(job)

    print(f"  Already applied: {skipped}")
    print(f"  Fresh jobs: {len(fresh_jobs)}")

    # Score and sort
    for job in fresh_jobs:
        job["relevance_score"] = score_job(job, target_titles, min_salary)

    fresh_jobs.sort(key=lambda j: j["relevance_score"], reverse=True)

    # Take top N
    selected = fresh_jobs[:jobs_per_day]

    print(f"\n  Top {len(selected)} selected:")
    for i, job in enumerate(selected, 1):
        print(f"    {i:2}. [{job['relevance_score']:3}] {job['title'][:50]} — {job['company']}")

    # Save
    output_path = os.path.join(tmp_dir, "selected_jobs.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(selected, f, indent=2, ensure_ascii=False)

    print(f"\n  Saved to: {output_path}")
    return selected


if __name__ == "__main__":
    select_top_10()
