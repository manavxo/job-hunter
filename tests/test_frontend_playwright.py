"""
End-to-end FRONTEND tests for the Job Hunter dashboard.

These drive the REAL static dashboard (frontend/index.html) in a headless
Chromium browser (Playwright sync API) against a REAL uvicorn server running in a
subprocess on a dedicated port. They prove the frontend wiring works end-to-end:
page load, no JS console/page errors, tab switching, settings populate + save
round-trip, and table rendering for seeded jobs/applications.

Isolation:
- A fresh temp SQLite file is used as DB_PATH. It is set in os.environ BEFORE
  `import database` in THIS process, and the SAME DB_PATH is handed to the
  uvicorn subprocess, so both processes share one throwaway DB and never touch
  backend/jobhunter.db.
- We never click "Scrape Now" / "Run Now" / "Test Run" (those hit live job
  boards and the real LLM). We seed data directly via the database module and
  exercise only UI wiring + the settings round-trip.

Run:
    .venv/Scripts/python.exe -m pytest tests/test_frontend_playwright.py -v
"""

from __future__ import annotations

import os
import sys
import socket
import subprocess
import tempfile
import time

import pytest
import requests

# ---------------------------------------------------------------------------
# Paths / DB isolation — must set DB_PATH before importing `database`.
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
_VENV_PYTHON = os.path.join(_ROOT, ".venv", "Scripts", "python.exe")

# A dedicated throwaway DB file shared by this process and the uvicorn subprocess.
_TMP_DIR = tempfile.mkdtemp(prefix="jobhunter_fe_test_")
_TMP_DB = os.path.join(_TMP_DIR, "fe_test.db")
os.environ["DB_PATH"] = _TMP_DB

# Make `import database` resolve to backend/ and bind it to our temp DB.
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import database as db  # noqa: E402  (import after DB_PATH/sys.path are set)

HOST = "127.0.0.1"
PORT = 8011
BASE_URL = f"http://{HOST}:{PORT}"


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
SEED_SETTINGS = {
    "candidate": {
        "name": "Seed Candidate",
        "email": "seed.candidate@example.com",
        "phone": "+1-555-000-1111",
        "location": "Vancouver, BC",
        "linkedin": "https://linkedin.com/in/seed",
        "title_target": "Project Manager",
    },
    "search": {
        "job_titles": ["Project Manager", "Program Manager"],
        "locations": ["Vancouver, BC", "Remote"],
        "platforms": ["linkedin", "indeed"],
        "region": "ca",
        "distance_miles": 25,
        "hours_old": 24,
        "jobs_per_day": 10,
        "min_salary": 0,
    },
    "resume_mode": "honest",
    "llm": {
        "api_base": "https://openrouter.ai/api/v1",
        "api_key": "sk-seed-test-key-123456",
        "model": "openai/gpt-4o-mini",
        "max_tokens": 2000,
        "temperature": 0.7,
    },
    "email": {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "seed@gmail.com",
        "password": "seed app password",
        "from_name": "Seed Candidate",
        "from_email": "seed@gmail.com",
    },
    "base_resume": "# Seed Candidate\n\n## Summary\nExperienced project manager.",
    "base_cover_letter": "Dear Hiring Team,\n\nI am excited to apply.\n\nBest,\nSeed",
}

SEED_JOBS = [
    {
        "id": "fe-ext-1", "title": "Senior Project Manager", "company": "Acme Robotics",
        "location": "Vancouver, BC", "description": "Lead programs.",
        "job_url": "https://www.linkedin.com/jobs/view/111", "date_posted": "",
        "site": "linkedin", "salary_min": "100000", "salary_max": "140000",
        "relevance_score": 88,
    },
    {
        "id": "fe-ext-2", "title": "Program Manager", "company": "Beta Logistics",
        "location": "Remote", "description": "Coordinate cross-functional work.",
        "job_url": "https://www.indeed.com/viewjob?jk=222", "date_posted": "",
        "site": "indeed", "salary_min": "", "salary_max": "",
        "relevance_score": 75,
    },
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


@pytest.fixture(scope="module")
def server():
    """Launch a real uvicorn server in a subprocess sharing our temp DB."""
    if _port_open(HOST, PORT):
        pytest.fail(
            f"Port {PORT} is already in use; cannot launch an isolated test server."
        )

    python = _VENV_PYTHON if os.path.exists(_VENV_PYTHON) else sys.executable
    env = dict(os.environ)
    env["DB_PATH"] = _TMP_DB  # subprocess MUST use the same throwaway DB

    proc = subprocess.Popen(
        [python, "-m", "uvicorn", "main:app", "--host", HOST, "--port", str(PORT)],
        cwd=_BACKEND,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Poll /api/health until ready (timeout ~30s).
    deadline = time.time() + 30
    ready = False
    while time.time() < deadline:
        if proc.poll() is not None:
            out = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
            pytest.fail(f"uvicorn subprocess exited early (code {proc.returncode}).\n{out}")
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=1)
            if r.status_code == 200:
                ready = True
                break
        except requests.RequestException:
            pass
        time.sleep(0.3)

    if not ready:
        proc.terminate()
        try:
            out = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
        except Exception:  # noqa: BLE001
            out = ""
        pytest.fail(f"Server did not become healthy within 30s.\n{out}")

    yield BASE_URL

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="module")
def seeded(server):
    """
    Seed settings (via HTTP API) and jobs/applications (via the database module)
    BEFORE the browser tests run. Returns the seeded settings for assertions.
    """
    # Settings via the real API so the subprocess owns the write.
    r = requests.put(f"{server}/api/settings", json=SEED_SETTINGS, timeout=10)
    r.raise_for_status()

    # Jobs + applications directly into the shared DB (avoids hitting live boards).
    db.insert_jobs(SEED_JOBS)
    db.insert_application(
        job_id=1, title="Senior Project Manager", company="Acme Robotics",
        contact_name="Jane Lee", contact_email="jane.lee@acme.com",
        contact_source="verified", resume_text="resume A", cover_letter="cover A",
        resume_mode="honest", style_variant="achievement-focused",
        apply_method="linkedin_easy_apply", apply_status="applied",
        outreach_status="sent",
    )
    db.insert_application(
        job_id=2, title="Program Manager", company="Beta Logistics",
        contact_name="", contact_email="", contact_source="",
        resume_text="resume B", cover_letter="cover B",
        resume_mode="honest", style_variant="concise",
        apply_method="external_redirect", apply_status="applied",
        outreach_status="skipped",
    )

    # Sanity: the subprocess must SEE the rows we just inserted (shared DB).
    jobs = requests.get(f"{server}/api/jobs", timeout=10).json()
    assert any(j["company"] == "Acme Robotics" for j in jobs), (
        "Subprocess does not see seeded jobs — DB is not shared correctly."
    )
    return SEED_SETTINGS


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


class _ConsoleCollector:
    """Attach to a page to capture console errors and uncaught page errors."""

    def __init__(self, page):
        self.console_errors = []
        self.page_errors = []
        page.on("console", self._on_console)
        page.on("pageerror", self._on_pageerror)

    def _on_console(self, msg):
        if msg.type == "error":
            self.console_errors.append(msg.text)

    def _on_pageerror(self, exc):
        self.page_errors.append(str(exc))


@pytest.fixture()
def page(browser, seeded):
    page = browser.new_page()
    collector = _ConsoleCollector(page)
    page._console_collector = collector  # stash for tests that want to assert clean
    yield page
    page.close()


def _goto_home(page):
    page.goto(BASE_URL, wait_until="networkidle")


def _open_tab(page, tab_name: str):
    """Click a nav tab and wait for its content to become active."""
    page.click(f'.nav-tab[data-tab="{tab_name}"]')
    page.wait_for_selector(f"#tab-{tab_name}.active", timeout=5000)


# ---------------------------------------------------------------------------
# 1. Page loads
# ---------------------------------------------------------------------------
def test_page_loads_title_and_header(page):
    _goto_home(page)
    assert page.title() == "Job Hunter"
    header = page.locator("header h1")
    assert header.is_visible()
    assert "Job Hunter" in header.inner_text()


# ---------------------------------------------------------------------------
# 2. No JS console errors / uncaught page errors on load
# ---------------------------------------------------------------------------
def test_no_console_or_page_errors_on_load(page):
    _goto_home(page)
    # Give the initial loadDashboard() fetches time to complete.
    page.wait_for_timeout(800)
    c = page._console_collector
    assert not c.console_errors, f"Console errors on load: {c.console_errors}"
    assert not c.page_errors, f"Uncaught page errors on load: {c.page_errors}"


# ---------------------------------------------------------------------------
# 3. Tab navigation
# ---------------------------------------------------------------------------
def test_tab_navigation_switches_active_content(page):
    _goto_home(page)
    # Dashboard active by default.
    assert page.locator("#tab-dashboard").get_attribute("class").find("active") != -1

    for tab in ("jobs", "applications", "settings", "dashboard"):
        _open_tab(page, tab)
        # The matching content is active and visible.
        assert page.locator(f"#tab-{tab}").is_visible()
        assert "active" in (page.locator(f"#tab-{tab}").get_attribute("class") or "")
        # Every OTHER tab-content is hidden.
        for other in ("dashboard", "jobs", "applications", "settings"):
            if other == tab:
                continue
            assert not page.locator(f"#tab-{other}").is_visible(), (
                f"#tab-{other} should be hidden while {tab} is active"
            )
        # The clicked nav button is the active one.
        assert "active" in (
            page.locator(f'.nav-tab[data-tab="{tab}"]').get_attribute("class") or ""
        )


# ---------------------------------------------------------------------------
# 4. Settings load — fields populate from seeded settings; platforms + radios render
# ---------------------------------------------------------------------------
def test_settings_tab_populates_from_api(page, seeded):
    _goto_home(page)
    _open_tab(page, "settings")
    page.wait_for_function(
        "document.getElementById('set-name').value.length > 0", timeout=5000
    )

    assert page.input_value("#set-name") == seeded["candidate"]["name"]
    assert page.input_value("#set-email") == seeded["candidate"]["email"]
    assert page.input_value("#set-phone") == seeded["candidate"]["phone"]
    assert page.input_value("#set-location") == seeded["candidate"]["location"]
    assert page.input_value("#set-title-target") == seeded["candidate"]["title_target"]

    # Job titles joined with ", "
    assert page.input_value("#set-titles") == ", ".join(seeded["search"]["job_titles"])
    # Region select reflects the stored value.
    assert page.input_value("#set-region") == seeded["search"]["region"]

    # Platform checkboxes rendered from /api/platforms.
    page.wait_for_selector(".platform-cb", timeout=5000)
    cb_values = page.locator(".platform-cb").evaluate_all(
        "els => els.map(e => e.value)"
    )
    assert "linkedin" in cb_values and "indeed" in cb_values
    # Seeded platforms are checked.
    assert page.is_checked('.platform-cb[value="linkedin"]')
    assert page.is_checked('.platform-cb[value="indeed"]')

    # Resume-mode radios exist (honest + enhanced) and seeded mode is selected.
    assert page.locator('input[name="resume-mode"]').count() == 2
    assert page.is_checked('input[name="resume-mode"][value="honest"]')

    # Credential inputs render for login platforms (linkedin/indeed).
    page.wait_for_selector(".cred-pass", timeout=5000)
    cred_platforms = page.locator(".cred-pass").evaluate_all(
        "els => els.map(e => e.dataset.platform)"
    )
    assert "linkedin" in cred_platforms and "indeed" in cred_platforms


# ---------------------------------------------------------------------------
# 5. Settings SAVE round-trip
# ---------------------------------------------------------------------------
def test_settings_save_round_trip(page):
    _goto_home(page)
    _open_tab(page, "settings")
    page.wait_for_function(
        "document.getElementById('set-name').value.length > 0", timeout=5000
    )

    new_name = "Round Trip Candidate"
    new_titles = "QA Lead, Test Manager"
    new_pass = "linkedin-secret-xyz"

    page.fill("#set-name", new_name)
    page.fill("#set-titles", new_titles)
    # Toggle a platform: ensure glassdoor (a login platform not seeded) is checked.
    if not page.is_checked('.platform-cb[value="glassdoor"]'):
        page.check('.platform-cb[value="glassdoor"]')
    # Choose the "enhanced" resume mode radio.
    page.check('input[name="resume-mode"][value="enhanced"]')
    # Type a LinkedIn credential password (frontend only sends when typed).
    page.fill('.cred-pass[data-platform="linkedin"]', new_pass)

    # Save.
    page.click('button:has-text("Save All Settings")')
    # Wait for the success toast.
    page.wait_for_selector("#toast.show", timeout=5000)
    toast_text = page.locator("#toast").inner_text()
    assert "Settings saved" in toast_text, f"Unexpected toast: {toast_text!r}"

    # Verify persistence via the API (the subprocess owns the DB).
    settings = requests.get(f"{BASE_URL}/api/settings", timeout=10).json()
    assert settings["candidate"]["name"] == new_name
    assert settings["search"]["job_titles"] == ["QA Lead", "Test Manager"]
    assert "glassdoor" in settings["search"]["platforms"]
    assert settings["resume_mode"] == "enhanced"

    # The credential password should be stored. The API masks it but flags it set.
    creds = settings.get("platform_credentials", {})
    assert "linkedin" in creds, f"linkedin credentials missing: {creds}"
    assert creds["linkedin"].get("password_set") is True, (
        f"linkedin password not persisted (no password_set flag): {creds['linkedin']}"
    )

    # And confirm the raw password really landed in the DB (not just the flag).
    raw_creds = db.get_setting("platform_credentials", {})
    assert raw_creds.get("linkedin", {}).get("password") == new_pass, (
        "Typed credential password was not stored in the DB."
    )


# ---------------------------------------------------------------------------
# 6. Jobs + Applications tables render seeded rows
# ---------------------------------------------------------------------------
def test_jobs_table_renders_seeded_rows(page):
    _goto_home(page)
    _open_tab(page, "jobs")
    page.wait_for_selector("#jobs-table tr", timeout=5000)
    body = page.locator("#jobs-table").inner_text()
    assert "Senior Project Manager" in body
    assert "Acme Robotics" in body
    assert "Program Manager" in body
    assert "Beta Logistics" in body


def test_applications_table_renders_seeded_rows(page):
    _goto_home(page)
    _open_tab(page, "applications")
    page.wait_for_selector("#all-apps-table tr", timeout=5000)
    body = page.locator("#all-apps-table").inner_text()
    assert "Senior Project Manager" in body
    assert "Acme Robotics" in body
    assert "Jane Lee" in body
    # Status badges rendered.
    assert "applied" in body.lower()


# ---------------------------------------------------------------------------
# 7. Empty state — Jobs table shows empty-state text when there are no jobs.
# This uses a FRESH page WITHOUT the `seeded` fixture, against a clean DB
# state. We assert against the JS-rendered empty message string by intercepting
# the /api/jobs response to return an empty list (no production code touched).
# ---------------------------------------------------------------------------
def test_jobs_empty_state(browser, server):
    page = browser.new_page()
    try:
        # Force /api/jobs to return [] so we exercise the empty-state branch
        # regardless of seeded data, without mutating the DB.
        page.route(
            "**/api/jobs*",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body="[]",
            ),
        )
        page.goto(BASE_URL, wait_until="networkidle")
        page.click('.nav-tab[data-tab="jobs"]')
        page.wait_for_selector("#tab-jobs.active", timeout=5000)
        page.wait_for_selector("#jobs-table .empty", timeout=5000)
        empty_text = page.locator("#jobs-table .empty").inner_text()
        assert "No jobs scraped yet" in empty_text
    finally:
        page.close()
