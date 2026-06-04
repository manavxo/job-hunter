"""
Shared pytest fixtures for the Job Hunter test suite.

Key isolation guarantees:
- Tests run against a TEMP SQLite database (DB_PATH env set before importing the
  backend), so they never read or mutate the real backend/jobhunter.db.
- The API is exercised in-process via Starlette's TestClient (no network, no port).
- External services (job boards, the LLM, SMTP, the browser) are mocked by the
  `patch_externals` fixture so pipeline tests are fast and deterministic.
"""

import os
import sys
import tempfile

import pytest

# --- Isolate the database BEFORE importing the backend -----------------------
_TMP_DB = os.path.join(tempfile.mkdtemp(prefix="jobhunter_test_"), "test.db")
os.environ["DB_PATH"] = _TMP_DB

# Make `import database` / `from pipeline import ...` resolve to backend/
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import database as db          # noqa: E402
import main                    # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


# --- Fake data the pipeline mocks return -------------------------------------
FAKE_JOBS = [
    {
        "id": "ext-1", "title": "Project Manager", "company": "Acme Corp",
        "location": "Vancouver, BC", "description": "Lead projects. " * 40,
        "job_url": "https://www.linkedin.com/jobs/view/1", "date_posted": "",
        "site": "linkedin", "salary_min": "90000", "salary_max": "120000",
    },
    {
        "id": "ext-2", "title": "Project Coordinator", "company": "Beta Inc",
        "location": "Vancouver, BC", "description": "Coordinate projects. " * 40,
        "job_url": "https://www.indeed.com/viewjob?jk=2", "date_posted": "",
        "site": "indeed", "salary_min": "", "salary_max": "",
    },
]

FAKE_ENRICHMENT = {
    "resume": "# Test Candidate\n\nVancouver, BC | x@y.com\n\n## Professional Summary\nTailored.",
    "cover_letter": "Dear Hiring Team,\n\nI am genuinely excited about this specific role.\n\nBest,\nTest",
    "style_variant": "achievement-focused",
    "skills_matched": ["scheduling", "budgeting"],
    "gaps_filled": [],
}


@pytest.fixture(scope="session")
def client():
    """In-process API client. Runs the app lifespan once (init_db + scheduler)."""
    with TestClient(main.app) as c:
        yield c


@pytest.fixture()
def fresh_db():
    """Wipe all tables before a test so each test starts clean."""
    db.init_db()
    conn = db.get_db()
    conn.execute("DELETE FROM jobs")
    conn.execute("DELETE FROM applications")
    conn.execute("DELETE FROM settings")
    conn.commit()
    conn.close()
    return db


@pytest.fixture()
def patch_externals(monkeypatch):
    """
    Replace every external dependency of the pipeline with a deterministic stub.
    Returns a dict of call-recording lists so tests can assert what happened.
    """
    calls = {"apply": [], "send": [], "enrich": [], "contact": [], "pdf": []}

    def fake_scrape_jobs(_search):
        return [dict(j) for j in FAKE_JOBS]

    def fake_enrich(job, *_a, **kw):
        calls["enrich"].append({"job": job.get("title"), "mode": kw.get("resume_mode"),
                                "style_index": kw.get("style_index")})
        return dict(FAKE_ENRICHMENT)

    def fake_find_contact(job):
        calls["contact"].append(job.get("title"))
        return {"name": "Jane Lee", "email": "jane.lee@acme.com", "title": "Hiring Manager",
                "company": job.get("company", ""), "source": "verified"}

    def fake_apply(job, *_a, **_kw):
        calls["apply"].append(job.get("title"))
        return {"status": "applied", "method": "linkedin_easy_apply", "error": None}

    def fake_send(*_a, **_kw):
        calls["send"].append(_a[1] if len(_a) > 1 else _kw.get("to_email"))
        return True

    def fake_pdf(*_a, **_kw):
        calls["pdf"].append(True)
        return None  # skip real PDF in pipeline tests

    monkeypatch.setattr(main.scrape, "scrape_jobs", fake_scrape_jobs)
    monkeypatch.setattr(main.enrich, "enrich_application", fake_enrich)
    monkeypatch.setattr(main.contacts, "find_contact", fake_find_contact)
    monkeypatch.setattr(main.applier, "apply_to_job", fake_apply)
    monkeypatch.setattr(main.send, "send_email", fake_send)
    monkeypatch.setattr(main.resume_pdf, "render_resume_pdf", fake_pdf)
    return calls
