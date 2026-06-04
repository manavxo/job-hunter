"""
Interactive setup wizard for Job Hunter.

Walks the user through filling in config.yaml with their details,
testing API connections, and verifying everything works.

Usage:
    python tools/setup_wizard.py              # full setup
    python tools/setup_wizard.py --check      # verify existing config
    python tools/setup_wizard.py --env        # create .env from template
"""

import argparse
import json
import os
import sys

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def prompt(default, label, required=True):
    """Prompt user for input with a default value."""
    display = f"  {label}"
    if default and str(default) not in ("", "None", "FRIEND_NAME_HERE", "APOLLO_API_KEY_HERE",
                                         "friend@email.com", "+1-555-000-0000",
                                         "https://linkedin.com/in/friend-profile",
                                         "City, State", "your.email@gmail.com",
                                         "GMAIL_APP_PASSWORD_HERE"):
        display += f" [{default}]"
    display += ": "

    value = input(display).strip()
    if not value:
        if required and (not default or str(default) in ("", "FRIEND_NAME_HERE",
                                                          "friend@email.com",
                                                          "+1-555-000-0000",
                                                          "City, State")):
            print("    ⚠ This field is required.")
            return prompt(default, label, required)
        return default
    return value


def test_apollo(api_key):
    """Test Apollo API connection."""
    import requests
    try:
        resp = requests.post(
            "https://api.apollo.io/v1/mixed_people/search",
            json={"api_key": api_key, "q_organization_name": "Google", "per_page": 1},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("people"):
                print("    ✓ Apollo API working")
                return True
            else:
                print("    ⚠ Apollo responded but no results (key may be invalid)")
                return False
        elif resp.status_code == 422:
            print("    ⚠ Apollo API key rejected")
            return False
        else:
            print(f"    ⚠ Apollo HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"    ✗ Apollo connection failed: {e}")
        return False


def test_smtp(config):
    """Test SMTP connection."""
    import smtplib
    email_cfg = config["email"]
    try:
        with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"]) as server:
            server.starttls()
            server.login(email_cfg["username"], email_cfg["password"])
            print("    ✓ SMTP connection working")
            return True
    except Exception as e:
        print(f"    ✗ SMTP failed: {e}")
        return False


def test_llm(config):
    """Test LLM API connection."""
    import requests
    llm = config.get("llm", {})
    api_base = llm.get("api_base", "https://openrouter.ai/api/v1")
    api_key = llm.get("api_key", "")
    model = llm.get("model", "openai/gpt-4o-mini")

    if not api_key:
        print("    ⚠ No LLM API key set")
        return False

    try:
        resp = requests.post(
            f"{api_base}/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Say 'ok' and nothing else."}],
                "max_tokens": 5,
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 200:
            print(f"    ✓ LLM API working ({model})")
            return True
        else:
            print(f"    ✗ LLM API error {resp.status_code}: {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"    ✗ LLM connection failed: {e}")
        return False


def run_setup():
    """Interactive setup wizard."""
    config = load_config()

    print(f"\n{'='*60}")
    print("  JOB HUNTER — Setup Wizard")
    print(f"{'='*60}")
    print("  Fill in your details. Press Enter to keep existing values.\n")

    # --- Candidate ---
    print("─── YOUR DETAILS ─────────────────────────────────")
    c = config["candidate"]
    c["name"] = prompt(c.get("name"), "Full name")
    c["email"] = prompt(c.get("email"), "Email address")
    c["phone"] = prompt(c.get("phone"), "Phone number")
    c["linkedin"] = prompt(c.get("linkedin"), "LinkedIn URL")
    c["location"] = prompt(c.get("location"), "City, State (or 'Remote')")
    c["title_target"] = prompt(c.get("title_target"), "Target job title")

    # --- Search ---
    print("\n─── JOB SEARCH SETTINGS ─────────────────────────")
    s = config["search"]
    titles_raw = prompt(", ".join(s.get("job_titles", [])), "Job titles (comma-separated)")
    s["job_titles"] = [t.strip() for t in titles_raw.split(",")]
    locs_raw = prompt(", ".join(s.get("locations", [])), "Locations (comma-separated, or 'Remote')")
    s["locations"] = [l.strip() for l in locs_raw.split(",")]
    s["jobs_per_day"] = int(prompt(str(s.get("jobs_per_day", 10)), "Jobs per day"))
    s["hours_old"] = int(prompt(str(s.get("hours_old", 24)), "Max hours old"))
    min_sal = prompt(str(s.get("min_salary", 0)), "Minimum salary (0 to disable)")
    s["min_salary"] = int(min_sal)

    # --- LLM ---
    print("\n─── LLM CONFIGURATION ───────────────────────────")
    print("  Any OpenAI-compatible API works (OpenRouter, OpenAI, etc.)")
    llm = config.get("llm", {})
    llm["api_base"] = prompt(
        llm.get("api_base", "https://openrouter.ai/api/v1"),
        "API base URL"
    )
    llm["api_key"] = prompt(llm.get("api_key", ""), "API key", required=True)
    llm["model"] = prompt(
        llm.get("model", "openai/gpt-4o-mini"),
        "Model name"
    )
    config["llm"] = llm

    # --- Apollo ---
    print("\n─── APOLLO.IO (Hiring Manager Lookup) ───────────")
    print("  Get your key at: https://apollo.io → Settings → API Keys")
    print("  Free tier: 50 credits/month. Leave blank to skip.")
    apollo = config.get("apollo", {})
    apollo["api_key"] = prompt(apollo.get("api_key", ""), "Apollo API key (or 'skip')", required=False)
    if apollo["api_key"] == "skip":
        apollo["api_key"] = ""
    config["apollo"] = apollo

    # --- Email ---
    print("\n─── EMAIL (Gmail SMTP) ──────────────────────────")
    print("  Need a Gmail App Password:")
    print("  Google Account → Security → 2-Step Verification → App Passwords")
    email = config.get("email", {})
    email["username"] = prompt(email.get("username", ""), "Gmail address", required=True)
    email["password"] = prompt(email.get("password", ""), "Gmail App Password", required=True)
    email["from_name"] = c["name"]
    email["from_email"] = email["username"]
    email["signature"] = f"Best regards,\n{c['name']}\n{c['phone']} | {c['linkedin']}"
    config["email"] = email

    # Save
    save_config(config)
    print(f"\n  ✓ Config saved to {CONFIG_PATH}")

    # --- Test connections ---
    print("\n─── TESTING CONNECTIONS ─────────────────────────")
    config = load_config()

    print("  LLM API:")
    test_llm(config)

    if config["apollo"].get("api_key"):
        print("  Apollo API:")
        test_apollo(config["apollo"]["api_key"])

    print("  Gmail SMTP:")
    test_smtp(config)

    print(f"\n{'='*60}")
    print("  SETUP COMPLETE")
    print(f"{'='*60}")
    print("\n  Next steps:")
    print("  1. Edit base_resume.md with your real resume content")
    print("  2. Edit base_cover_letter.md with your cover letter template")
    print("  3. Run: python tools/daily_hunt.py --skip-send  (dry run)")
    print("  4. When ready: python tools/daily_hunt.py  (send real emails)")


def check_config():
    """Verify existing config is complete."""
    config = load_config()
    issues = []

    c = config.get("candidate", {})
    if not c.get("name") or c["name"] == "FRIEND_NAME_HERE":
        issues.append("candidate.name not set")
    if not c.get("email") or c["email"] == "friend@email.com":
        issues.append("candidate.email not set")

    llm = config.get("llm", {})
    if not llm.get("api_key"):
        issues.append("llm.api_key not set (needed for resume customization)")

    email = config.get("email", {})
    if not email.get("username") or email["username"] == "your.email@gmail.com":
        issues.append("email.username not set")
    if not email.get("password") or email["password"] == "GMAIL_APP_PASSWORD_HERE":
        issues.append("email.password not set")

    if issues:
        print("\n  ⚠ Config issues found:")
        for issue in issues:
            print(f"    - {issue}")
        print(f"\n  Run: python tools/setup_wizard.py")
        return False
    else:
        print("\n  ✓ Config looks complete")
        return True


def main():
    parser = argparse.ArgumentParser(description="Job Hunter setup wizard")
    parser.add_argument("--check", action="store_true", help="Verify existing config")
    parser.add_argument("--env", action="store_true", help="Create .env file")
    args = parser.parse_args()

    if args.check:
        check_config()
    else:
        run_setup()


if __name__ == "__main__":
    main()
