"""
Daily Hunt Orchestrator — runs the full job application pipeline.

Calls all tools in sequence:
1. Scrape jobs (scrape_jobs.py)
2. Select top 10 (select_top_10.py)
3. Look up contacts (apollo_lookup.py)
4. Customize resume + cover letter (customize_materials.py)
5. Generate PDFs (generate_pdf.py)
6. Send emails (send_outreach.py)

Usage:
    python tools/daily_hunt.py              # full pipeline
    python tools/daily_hunt.py --skip-send  # dry run (don't send emails)
    python tools/daily_hunt.py --skip-scrape  # use existing scraped data
"""

import argparse
import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)


def run_step(name, func, *args, **kwargs):
    """Run a pipeline step with error handling."""
    print(f"\n{'='*60}")
    print(f"  STEP: {name}")
    print(f"{'='*60}")
    try:
        result = func(*args, **kwargs)
        return result
    except Exception as e:
        print(f"\n  ✗ FAILED: {name}")
        print(f"    Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Run the daily job hunt pipeline")
    parser.add_argument("--skip-send", action="store_true", help="Don't send emails (dry run)")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip scraping (use existing .tmp/today_jobs.json)")
    parser.add_argument("--skip-customize", action="store_true", help="Skip LLM customization")
    args = parser.parse_args()

    print(f"\n{'#'*60}")
    print(f"  JOB HUNTER — Daily Pipeline")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    # Step 1: Scrape
    if not args.skip_scrape:
        from scrape_jobs import main as scrape_main
        jobs = run_step("Scrape Job Boards", scrape_main)
        if jobs is None:
            print("\n  Pipeline aborted — scrape failed.")
            sys.exit(1)

    # Step 2: Select top 10
    from select_top_10 import select_top_10
    selected = run_step("Select Top 10", select_top_10)
    if selected is None:
        print("\n  Pipeline aborted — selection failed.")
        sys.exit(1)

    if not selected:
        print("\n  No new jobs to apply to today. Done.")
        return

    # Step 3: Find contacts (free — no API key needed)
    from contact_finder import main as contact_main
    contacts = run_step("Find Hiring Managers", contact_main)
    if contacts is None:
        print("\n  Pipeline aborted — contact lookup failed.")
        sys.exit(1)

    # Step 4: Customize resume + cover letter
    if not args.skip_customize:
        from customize_materials import main as customize_main
        run_step("Customize Resume & Cover Letter", customize_main)
    else:
        print(f"\n{'='*60}")
        print(f"  STEP: Customize Materials (SKIPPED)")
        print(f"{'='*60}")

    # Step 5: Generate PDFs
    from generate_pdf import main as pdf_main
    run_step("Generate PDF Resumes", pdf_main)

    # Step 6: Send emails
    if not args.skip_send:
        from send_outreach import main as send_main
        run_step("Send Outreach Emails", send_main)
    else:
        print(f"\n{'='*60}")
        print(f"  STEP: Send Emails (SKIPPED — dry run)")
        print(f"{'='*60}")

    # Summary
    print(f"\n{'#'*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    # Show what was produced
    import yaml
    config_path = os.path.join(PROJECT_DIR, "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    apps_dir = os.path.join(PROJECT_DIR, config["paths"]["tmp_dir"], "applications")
    if os.path.isdir(apps_dir):
        resumes = [f for f in os.listdir(apps_dir) if f.endswith("_resume.md")]
        covers = [f for f in os.listdir(apps_dir) if f.endswith("_cover.md")]
        contacts = [f for f in os.listdir(apps_dir) if f.endswith("_contact.json")]
        pdfs = [f for f in os.listdir(apps_dir) if f.endswith("_resume.pdf")]

        print(f"\n  Applications prepared: {len(resumes)}")
        print(f"  Cover letters written: {len(covers)}")
        print(f"  Contacts found: {len(contacts)}")
        print(f"  PDFs generated: {len(pdfs)}")

    log_path = os.path.join(PROJECT_DIR, config["paths"]["applications_log"])
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            lines = [l for l in f.readlines() if l.strip()]
        sent = sum(1 for l in lines if '"sent"' in l)
        print(f"  Total emails sent (all time): {sent}")


if __name__ == "__main__":
    main()
