"""
Customize resume and cover letter for each job using an LLM.

Reads each job's description from .tmp/applications/{id}_job.json,
tailors the base resume and cover letter to match, and saves
customized versions as {id}_resume.md and {id}_cover.md.

Supports any OpenAI-compatible API (OpenRouter, OpenAI, Anthropic via proxy, local).

Usage:
    python tools/customize_materials.py                    # customize all jobs
    python tools/customize_materials.py --job-id 003      # customize single job
    python tools/customize_materials.py --dry-run          # show prompts only

Input:  .tmp/applications/{id}_job.json + base_resume.md + base_cover_letter.md
Output: .tmp/applications/{id}_resume.md + .tmp/applications/{id}_cover.md
"""

import argparse
import json
import os
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


def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def call_llm(config, system_prompt, user_prompt):
    """Call an OpenAI-compatible chat completions endpoint."""
    llm = config.get("llm", {})
    api_base = llm.get("api_base", "https://openrouter.ai/api/v1")
    api_key = llm.get("api_key", os.environ.get("OPENROUTER_API_KEY", ""))
    model = llm.get("model", "openai/gpt-4o-mini")
    max_tokens = llm.get("max_tokens", 2000)
    temperature = llm.get("temperature", 0.7)

    if not api_key:
        print("      ERROR: No LLM API key. Set llm.api_key in config.yaml or OPENROUTER_API_KEY env var.")
        return None

    url = f"{api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code == 429:
            print("      Rate limited — waiting 15s...")
            time.sleep(15)
            resp = requests.post(url, json=payload, headers=headers, timeout=60)

        if resp.status_code != 200:
            print(f"      LLM API error {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print(f"      LLM call failed: {e}")
        return None


def build_resume_prompt(job, base_resume, candidate):
    """Build the prompt for customizing a resume."""
    return f"""You are a professional resume writer. Customize this resume for the specific job below.

CANDIDATE: {candidate['name']}
TARGET ROLE: {job.get('title', 'Project Manager')} at {job.get('company', 'the company')}

JOB DESCRIPTION:
{job.get('description', 'No description available')[:3000]}

BASE RESUME:
{base_resume}

INSTRUCTIONS:
1. Reorder bullets so the most relevant experience comes first
2. Mirror keywords from the job description naturally (don't stuff)
3. Adjust the professional summary to match this specific role
4. Keep ALL the candidate's real experience — do not fabricate anything
5. Keep the same markdown format
6. Keep it to one page equivalent (concise)
7. If the JD mentions specific tools/methods (Agile, Jira, etc.) and the candidate has that experience, make sure it's prominent

Output ONLY the customized resume in markdown. No commentary."""


def build_cover_prompt(job, base_resume, base_cover, candidate):
    """Build the prompt for writing a cover letter."""
    return f"""You are writing a cover letter for {candidate['name']} applying to {job.get('title', 'the position')} at {job.get('company', 'the company')}.

JOB DESCRIPTION:
{job.get('description', 'No description available')[:3000]}

CANDIDATE'S RESUME:
{base_resume}

TEMPLATE TO FOLLOW:
{base_cover}

INSTRUCTIONS:
1. Open with a strong hook tied to the specific role and company
2. Reference 2-3 specific requirements from the JD and map them to real experience
3. Mention the company by name and reference something about their mission/product/team
4. Keep it under 250 words
5. Sound human — no AI-isms, no filler, no generic phrases
6. Close with a clear, confident call to action
7. Use the candidate's real experience only — do not fabricate achievements

Output ONLY the cover letter text. No subject line, no commentary."""


def customize_single(job_id, config, base_resume, base_cover, candidate, dry_run=False):
    """Customize resume + cover letter for one job."""
    tmp_dir = os.path.join(PROJECT_DIR, config["paths"]["tmp_dir"])
    apps_dir = os.path.join(tmp_dir, "applications")

    job_path = os.path.join(apps_dir, f"{job_id}_job.json")
    if not os.path.exists(job_path):
        print(f"  [{job_id}] Job file not found — skipping")
        return False

    with open(job_path, "r", encoding="utf-8") as f:
        job = json.load(f)

    title = job.get("title", "?")[:50]
    company = job.get("company", "?")
    print(f"\n  [{job_id}] {title} — {company}")

    # --- Resume ---
    resume_prompt = build_resume_prompt(job, base_resume, candidate)
    resume_system = "You are a professional resume writer who creates tailored, ATS-optimized resumes."

    if dry_run:
        print(f"      [DRY RUN] Resume prompt ({len(resume_prompt)} chars)")
        print(f"      [DRY RUN] Cover prompt will follow")
        return True

    print("      Customizing resume...", end=" ", flush=True)
    custom_resume = call_llm(config, resume_system, resume_prompt)
    if custom_resume:
        resume_path = os.path.join(apps_dir, f"{job_id}_resume.md")
        with open(resume_path, "w", encoding="utf-8") as f:
            f.write(custom_resume)
        print(f"✓ ({len(custom_resume)} chars)")
    else:
        print("✗ Failed — using base resume")
        resume_path = os.path.join(apps_dir, f"{job_id}_resume.md")
        with open(resume_path, "w", encoding="utf-8") as f:
            f.write(base_resume)

    # Small delay between LLM calls
    time.sleep(1)

    # --- Cover Letter ---
    cover_prompt = build_cover_prompt(job, base_resume, base_cover, candidate)
    cover_system = "You are a cover letter writer. You write concise, specific, human-sounding letters that get interviews."

    print("      Writing cover letter...", end=" ", flush=True)
    custom_cover = call_llm(config, cover_system, cover_prompt)
    if custom_cover:
        cover_path = os.path.join(apps_dir, f"{job_id}_cover.md")
        with open(cover_path, "w", encoding="utf-8") as f:
            f.write(custom_cover)
        print(f"✓ ({len(custom_cover)} chars)")
    else:
        print("✗ Failed — using template")
        cover_path = os.path.join(apps_dir, f"{job_id}_cover.md")
        with open(cover_path, "w", encoding="utf-8") as f:
            f.write(base_cover)

    return True


def main():
    parser = argparse.ArgumentParser(description="Customize resume + cover letter per job")
    parser.add_argument("--job-id", type=str, help="Process single job (e.g. 003)")
    parser.add_argument("--dry-run", action="store_true", help="Show prompts without calling LLM")
    args = parser.parse_args()

    config = load_config()
    candidate = config["candidate"]

    # Validate candidate info
    if candidate.get("name", "FRIEND_NAME_HERE") == "FRIEND_NAME_HERE":
        print("\n  ERROR: Candidate name not set in config.yaml")
        print("  Edit config.yaml and fill in the candidate section first.")
        sys.exit(1)

    # Load base materials
    resume_path = os.path.join(PROJECT_DIR, config["paths"]["resume_template"])
    cover_path = os.path.join(PROJECT_DIR, config["paths"]["cover_letter_template"])

    if not os.path.exists(resume_path):
        print(f"  ERROR: Resume template not found at {resume_path}")
        sys.exit(1)

    base_resume = load_text(resume_path)
    base_cover = load_text(cover_path) if os.path.exists(cover_path) else ""

    # Find jobs to process
    tmp_dir = os.path.join(PROJECT_DIR, config["paths"]["tmp_dir"])
    apps_dir = os.path.join(tmp_dir, "applications")

    if not os.path.isdir(apps_dir):
        print("  ERROR: No applications directory. Run apollo_lookup.py first.")
        sys.exit(1)

    if args.job_id:
        job_ids = [args.job_id]
    else:
        job_files = sorted([f for f in os.listdir(apps_dir) if f.endswith("_job.json")])
        job_ids = [f.replace("_job.json", "") for f in job_files]

    if not job_ids:
        print("  No jobs to customize.")
        return

    print(f"\n{'='*60}")
    print(f"  CUSTOMIZE MATERIALS — {len(job_ids)} jobs")
    print(f"{'='*60}")

    success = 0
    for jid in job_ids:
        ok = customize_single(jid, config, base_resume, base_cover, candidate, dry_run=args.dry_run)
        if ok:
            success += 1

    print(f"\n  {'='*50}")
    print(f"  Customized: {success}/{len(job_ids)}")
    if args.dry_run:
        print(f"  (dry run — no LLM calls made)")


if __name__ == "__main__":
    main()
