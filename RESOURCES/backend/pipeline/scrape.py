"""
Job scraping via jobspy + custom scrapers.

Supports: LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter,
Craigslist, Monster, Dice, and any site jobspy supports.

Usage:
    from pipeline.scrape import scrape_jobs, score_job
"""

import re
import time
from datetime import datetime

import requests


# ---------------------------------------------------------------------------
# Platform registry
# ---------------------------------------------------------------------------
PLATFORMS = {
    "linkedin": {"name": "LinkedIn", "type": "jobspy"},
    "indeed": {"name": "Indeed", "type": "jobspy"},
    "glassdoor": {"name": "Glassdoor", "type": "jobspy"},
    "google": {"name": "Google Jobs", "type": "jobspy"},
    "zip_recruiter": {"name": "ZipRecruiter", "type": "jobspy"},
    "bing": {"name": "Bing Jobs", "type": "jobspy"},
    "craigslist": {"name": "Craigslist", "type": "custom"},
}


def get_available_platforms():
    """Return list of available platforms with their names."""
    return [
        {"id": k, "name": v["name"], "type": v["type"]}
        for k, v in PLATFORMS.items()
    ]


# ---------------------------------------------------------------------------
# Main scraper
# ---------------------------------------------------------------------------
def scrape_jobs(search_config):
    """
    Scrape job boards for fresh postings.

    Args:
        search_config: dict with keys:
            - job_titles: list of title strings
            - locations: list of location strings
            - platforms: list of platform IDs
            - region: country code (us, uk, ca, au, de, etc.)
            - distance_miles: int
            - hours_old: int

    Returns:
        list of job dicts
    """
    titles = search_config.get("job_titles", ["Project Manager"])
    locations = search_config.get("locations", ["Remote"])
    distance = search_config.get("distance_miles", 25)
    hours = search_config.get("hours_old", 24)
    platforms = search_config.get("platforms", ["linkedin", "indeed", "glassdoor", "google"])
    region = search_config.get("region", "us")

    # Map region codes to Indeed country names
    region_map = {
        "us": "USA", "uk": "United Kingdom", "ca": "Canada",
        "au": "Australia", "de": "Germany", "fr": "France",
        "in": "India", "br": "Brazil", "nl": "Netherlands",
        "sg": "Singapore", "ae": "UAE", "za": "South Africa",
    }
    country = region_map.get(region, "USA")

    # Split platforms by type
    jobspy_platforms = [p for p in platforms if PLATFORMS.get(p, {}).get("type") == "jobspy"]
    custom_platforms = [p for p in platforms if PLATFORMS.get(p, {}).get("type") == "custom"]

    all_jobs = []

    # Jobspy platforms
    if jobspy_platforms:
        all_jobs.extend(_scrape_jobspy(titles, locations, distance, hours, jobspy_platforms, country))

    # Custom platforms
    for platform in custom_platforms:
        if platform == "craigslist":
            all_jobs.extend(_scrape_craigslist(titles, locations, hours))

    # Dedupe by (title, company)
    seen = set()
    unique = []
    for job in all_jobs:
        key = (job["title"].lower().strip(), job["company"].lower().strip())
        if key not in seen and job["title"] and job["company"]:
            seen.add(key)
            unique.append(job)

    return unique


# ---------------------------------------------------------------------------
# Jobspy wrapper
# ---------------------------------------------------------------------------
def _scrape_jobspy(titles, locations, distance, hours, platforms, country="USA"):
    """Scrape using the jobspy library."""
    try:
        from jobspy import scrape_jobs as jobspy_scrape
    except ImportError:
        raise RuntimeError("jobspy not installed. Run: pip install python-jobspy")

    all_jobs = []

    for title in titles:
        for location in locations:
            try:
                jobs = jobspy_scrape(
                    site_name=platforms,
                    search_term=title,
                    location=location,
                    distance=distance,
                    results_wanted=50,
                    hours_old=hours,
                    country_indeed=country,
                )
                if jobs is not None and len(jobs) > 0:
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
                        }
                        all_jobs.append(job)
            except Exception:
                continue

    return all_jobs


# ---------------------------------------------------------------------------
# Craigslist custom scraper
# ---------------------------------------------------------------------------
def _scrape_craigslist(titles, locations, hours):
    """
    Scrape Craigslist job postings.

    Craigslist doesn't have an API, so we scrape the HTML search results.
    Uses the search URL pattern: https://{city}.craigslist.org/search/jjj?query={title}
    """
    all_jobs = []

    # Map location strings to Craigslist subdomains
    city_map = {
        "new york, ny": "newyork",
        "nyc": "newyork",
        "los angeles, ca": "losangeles",
        "la": "losangeles",
        "chicago, il": "chicago",
        "san francisco, ca": "sfbay",
        "sf": "sfbay",
        "seattle, wa": "seattle",
        "austin, tx": "austin",
        "boston, ma": "boston",
        "denver, co": "denver",
        "portland, or": "portland",
        "miami, fl": "miami",
        "atlanta, ga": "atlanta",
        "dallas, tx": "dallas",
        "houston, tx": "houston",
        "washington, dc": "washingtondc",
        "dc": "washingtondc",
        "philadelphia, pa": "philadelphia",
        "phoenix, az": "phoenix",
        "remote": "craigslist",  # Main site for remote
    }

    for title in titles:
        for location in locations:
            loc_lower = location.lower().strip()
            city = city_map.get(loc_lower, "craigslist")

            # For non-city matches, try to extract city from the location string
            if city == "craigslist" and loc_lower not in ("remote", ""):
                # Try to guess the subdomain
                clean = re.sub(r"[^a-z]", "", loc_lower)
                if clean:
                    city = clean

            url = f"https://{city}.craigslist.org/search/jjj"
            params = {
                "query": title,
                "srchType": "T",  # Title only
            }

            try:
                resp = requests.get(
                    url,
                    params=params,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                    timeout=15,
                )
                if resp.status_code != 200:
                    continue

                # Parse Craigslist HTML
                # CL uses <li class="cl-static-search-result"> for each listing
                listings = re.findall(
                    r'<li class="cl-static-search-result"[^>]*>.*?'
                    r'<a href="([^"]+)"[^>]*>.*?'
                    r'<div class="title">([^<]+)</div>.*?'
                    r'<div class="metadata">([^<]*)</div>',
                    resp.text,
                    re.DOTALL,
                )

                for link, title_text, metadata in listings:
                    # Extract date from metadata
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', metadata)
                    posted = date_match.group(1) if date_match else ""

                    job = {
                        "id": f"cl-{hash(link) % 100000}",
                        "title": title_text.strip(),
                        "company": "Craigslist Posting",
                        "location": location,
                        "description": f"Craigslist job posting: {title_text.strip()}",
                        "job_url": link if link.startswith("http") else f"https://{city}.craigslist.org{link}",
                        "date_posted": posted,
                        "site": "craigslist",
                        "salary_min": "",
                        "salary_max": "",
                    }
                    all_jobs.append(job)

                time.sleep(1)  # Be polite to Craigslist

            except Exception:
                continue

    return all_jobs


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def score_job(job, target_titles, min_salary=0):
    """Score a job 0-100 by relevance."""
    score = 0
    title = job.get("title", "").lower()
    desc = job.get("description", "").lower()

    # Title match (0-40)
    best = 0
    for target in target_titles:
        t = target.lower()
        if t in title:
            best = max(best, 40)
        elif any(w in title for w in t.split()):
            best = max(best, 25)
    score += best

    # Description quality (0-15)
    if len(desc) > 200:
        score += 15
    elif len(desc) > 50:
        score += 8

    # Salary info (0-15)
    sal_min = job.get("salary_min", "")
    if sal_min and sal_min not in ("", "None", "0"):
        try:
            sal = float(sal_min)
            if min_salary > 0 and sal < min_salary:
                score -= 30
            else:
                score += 15
        except (ValueError, TypeError):
            pass

    # Has URL (0-10)
    if job.get("job_url", "").startswith("http"):
        score += 10

    # Has company (0-10)
    if job.get("company", "") and len(job["company"]) > 1:
        score += 10

    # Recency (0-10)
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
