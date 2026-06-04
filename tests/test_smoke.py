"""Smoke test validating the test foundation (DB isolation, client, mocks)."""

import os


def test_db_is_temp():
    # We must be pointed at the throwaway DB, never the real one.
    assert "jobhunter_test_" in os.environ["DB_PATH"]


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_patch_externals_runs_pipeline(client, fresh_db, patch_externals):
    import main
    fresh_db.set_setting("candidate", {"name": "Test Candidate"})
    fresh_db.set_setting("search", {"job_titles": ["Project Manager"], "jobs_per_day": 5})
    fresh_db.set_setting("email", {"username": "me@gmail.com", "password": "x",
                                   "from_name": "Me", "from_email": "me@gmail.com"})
    main.run_daily_pipeline()
    assert len(patch_externals["apply"]) == 2          # both fake jobs applied
    assert patch_externals["send"]                      # outreach fired (verified contact)
    stats = fresh_db.get_application_stats()
    assert stats["applied"] == 2
