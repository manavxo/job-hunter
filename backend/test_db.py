"""Quick smoke test for database initialization."""
import database as db
import os

# Delete old DB for clean test
db_path = db.DB_PATH
if os.path.exists(db_path):
    os.remove(db_path)

db.init_db()
profiles = db.get_profiles()
print(f"Profiles: {len(profiles)}")
for p in profiles:
    print(f"  {p['id']}: {p['name']} ({p['role_template']})")

# Test profile settings isolation
db.set_profile_setting(1, "candidate", {"name": "Manav", "email": "manav@test.com"})
db.set_profile_setting(2, "candidate", {"name": "Girlfriend", "email": "gf@test.com"})

s1 = db.get_profile_setting(1, "candidate")
s2 = db.get_profile_setting(2, "candidate")
assert s1["name"] == "Manav", f"Expected Manav, got {s1}"
assert s2["name"] == "Girlfriend", f"Expected Girlfriend, got {s2}"
print("Settings isolation: OK")

# Test job scoping
job = {"id": "test-1", "title": "PM", "company": "Acme", "location": "NYC",
       "description": "Test job", "job_url": "https://example.com", "date_posted": "",
       "site": "test", "salary_min": "80000", "salary_max": "100000"}
db.insert_jobs([job], profile_id=1)
db.insert_jobs([job], profile_id=2)
j1 = db.get_new_jobs(10, profile_id=1)
j2 = db.get_new_jobs(10, profile_id=2)
assert len(j1) == 1, f"Expected 1 job for profile 1, got {len(j1)}"
assert len(j2) == 1, f"Expected 1 job for profile 2, got {len(j2)}"
# Same job can exist in both profiles (dedupe is per-profile)
print("Job scoping: OK")

# Test global settings
db.set_setting("access_code", "test123")
assert db.get_setting("access_code") == "test123"
print("Global settings: OK")

# Cleanup
os.remove(db_path)
print("\nAll database tests PASSED")