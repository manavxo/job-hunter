"""Test Phase 3: Browser manager and applier provisions."""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Test 1: BrowserManager imports and creates
from pipeline.browser import BrowserManager, get_browser_manager, shutdown_browser, retry_with_backoff
mgr = get_browser_manager()
assert isinstance(mgr, BrowserManager)
print("BrowserManager singleton: OK")

# Test 2: Start browser (Playwright is installed)
started = mgr.start()
assert started, "Browser failed to start (Playwright should be installed)"
assert mgr.available, "Browser should be available"
print(f"Browser start: OK (available={mgr.available})")

# Test 3: New context with anti-detection
ctx = mgr.new_context()
assert ctx is not None, "Context should not be None"
print("Browser context: OK")

# Test 4: Page context manager
with mgr.page() as (page, ctx2):
    assert page is not None, "Page should not be None"
    page.goto("data:text/html,<h1>Test</h1>")
    title = page.title()
    print(f"Page navigation: OK (title='{title}')")

    # Test 5: Security challenge detection (should be None on clean page)
    challenge = mgr.check_security_challenge(page)
    assert challenge is None, f"Expected no challenge, got {challenge}"
    print("Security check (clean page): OK")

    # Test 6: Screenshot capture
    ss_path = mgr._save_screenshot(page, "test")
    assert ss_path is not None, "Screenshot should succeed"
    assert os.path.exists(ss_path), "Screenshot file should exist"
    ss_size = os.path.getsize(ss_path)
    print(f"Screenshot: OK ({ss_size} bytes)")
    # Cleanup
    os.remove(ss_path)

# Test 7: retry_with_backoff works
attempt_count = 0
def flaky_func():
    global attempt_count
    attempt_count += 1
    if attempt_count < 3:
        raise ConnectionError("Transient error")
    return "success"

result = retry_with_backoff(flaky_func, max_retries=3, base_delay=0.1)
assert result == "success"
assert attempt_count == 3
print("Retry with backoff: OK")

# Test 8: Applier imports correctly
from pipeline.applier import apply_to_job, get_platform
assert get_platform("https://linkedin.com/jobs/123") == "linkedin"
assert get_platform("https://indeed.com/job/456") == "indeed"
assert get_platform("https://craigslist.org/789") == "craigslist"
assert get_platform("https://example.com/careers") == "external"
print("Applier imports + platform detection: OK")

# Test 9: Graceful handling when no credentials
candidate = {"name": "Test", "email": "test@test.com", "phone": "555-1234"}
job = {"job_url": "https://linkedin.com/jobs/123", "title": "PM", "company": "Acme"}
result = apply_to_job(job, {}, candidate, {})
assert result["status"] == "skipped"
assert "credentials" in result["error"].lower() or "not set" in result["error"].lower()
print("No credentials handling: OK")

# Cleanup
mgr.stop()
assert not mgr.available, "Browser should be stopped"
print("Browser stop: OK")

# Cleanup screenshots dir
import shutil
ss_dir = os.path.join(os.path.dirname(__file__), "..", ".tmp", "screenshots")
if os.path.exists(ss_dir):
    shutil.rmtree(ss_dir, ignore_errors=True)

print("\nAll Phase 3 tests PASSED")