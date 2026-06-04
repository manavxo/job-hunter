"""
Centralized Playwright browser session manager.

Provides a shared, managed browser lifecycle for all platform appliers.
Features:
- Single browser instance per pipeline run (reuse across jobs)
- Automatic screenshot capture on failures for debugging
- CAPTCHA/security challenge detection
- Retry logic with exponential backoff
- Graceful degradation when Playwright is unavailable
- Provision-only: does NOT break existing flows if Playwright isn't installed

Usage:
    from pipeline.browser import get_browser_manager

    mgr = get_browser_manager()
    with mgr.new_page() as page:
        page.goto("https://example.com")
        # ...
"""

from __future__ import annotations

import os
import time
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

logger = logging.getLogger("jobhunter.browser")

# Screenshot output directory
SCREENSHOT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    ".tmp",
    "screenshots",
)

# Platform-specific selectors that indicate security challenges
CAPTCHA_SELECTORS = [
    'iframe[src*="captcha"]',
    'iframe[src*="challenge"]',
    'iframe[src*="recaptcha"]',
    'iframe[src*="hcaptcha"]',
    '#captcha',
    '.captcha',
    '[class*="captcha"]',
    '[id*="captcha"]',
    'iframe[src*="arkose"]',
    '[data-testid="captcha"]',
]

SECURITY_INDICATORS = [
    'checkpoint',
    'challenge',
    'verify',
    'security',
    'suspicious',
    'robot',
    'unusual',
]


class BrowserManager:
    """
    Manages a shared Playwright browser instance with error recovery.

    Lifecycle:
        mgr = BrowserManager()
        mgr.start()
        # ... use mgr.new_page() as needed ...
        mgr.stop()

    Or use the module-level get_browser_manager() singleton.
    """

    def __init__(self, headless=True, screenshot_on_error=True):
        self._headless = headless
        self._screenshot_on_error = screenshot_on_error
        self._playwright = None
        self._browser = None
        self._available = False
        self._started = False

    @property
    def available(self) -> bool:
        """True if Playwright is installed and browser launched successfully."""
        return self._available

    def start(self) -> bool:
        """
        Launch the browser. Returns True if successful, False if Playwright
        is unavailable (graceful degradation).
        """
        if self._started:
            return self._available

        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self._headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            self._available = True
            self._started = True
            logger.info("Playwright browser launched (headless=%s)", self._headless)
            return True
        except ImportError:
            logger.info("Playwright not installed — browser automation disabled (provision only)")
            self._available = False
            self._started = False
            return False
        except Exception as exc:
            logger.warning("Failed to launch browser: %s — provision-only mode", exc)
            self._available = False
            self._started = False
            return False

    def stop(self):
        """Shut down the browser and Playwright."""
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._playwright = None
        self._available = False
        self._started = False
        logger.info("Browser stopped")

    def new_context(self, user_agent=None):
        """
        Create a new browser context with anti-detection settings.
        Returns None if browser is unavailable.
        """
        if not self._available or not self._browser:
            return None

        ua = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
        context = self._browser.new_context(
            user_agent=ua,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/New_York",
        )
        # Stealth: override navigator.webdriver
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        return context

    @contextmanager
    def page(self, user_agent=None):
        """
        Context manager that yields a (page, context) tuple.
        Automatically captures screenshots on exceptions if enabled.

        Usage:
            with mgr.page() as (page, ctx):
                page.goto(url)
        """
        context = self.new_context(user_agent)
        if context is None:
            yield None, None
            return

        page = context.new_page()
        try:
            yield page, context
        except Exception as exc:
            if self._screenshot_on_error:
                self._save_screenshot(page, "error")
            raise
        finally:
            try:
                context.close()
            except Exception:
                pass

    def check_security_challenge(self, page) -> Optional[str]:
        """
        Check if the page has a CAPTCHA or security challenge.
        Returns the challenge type string, or None if clear.
        """
        if page is None:
            return None

        # Check URL-based indicators
        url = page.url.lower()
        for indicator in SECURITY_INDICATORS:
            if indicator in url:
                return f"url_contains_{indicator}"

        # Check for CAPTCHA elements
        for selector in CAPTCHA_SELECTORS:
            try:
                if page.locator(selector).count() > 0:
                    return f"element:{selector}"
            except Exception:
                continue

        return None

    def _save_screenshot(self, page, tag="debug"):
        """Save a screenshot for debugging."""
        try:
            os.makedirs(SCREENSHOT_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize URL for filesystem — remove all non-alphanumeric chars
            import re as _re
            url_slug = _re.sub(r'[^a-zA-Z0-9]', '_', page.url[:60]).strip('_')
            filename = f"{ts}_{tag}_{url_slug}.png"
            path = os.path.join(SCREENSHOT_DIR, filename)
            page.screenshot(path=path, full_page=False)
            logger.info("Screenshot saved: %s", path)
            return path
        except Exception as exc:
            logger.warning("Screenshot capture failed: %s", exc)
            return None


def retry_with_backoff(func, max_retries=2, base_delay=2.0):
    """
    Retry a function with exponential backoff.
    Used for transient failures (network, timeout).
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as exc:
            if attempt == max_retries:
                raise
            delay = base_delay * (2 ** attempt)
            logger.info("Retry %d/%d after %.1fs: %s", attempt + 1, max_retries, delay, exc)
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Module-level singleton (lazy initialization)
# ---------------------------------------------------------------------------
_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """Get or create the global BrowserManager instance."""
    global _manager
    if _manager is None:
        _manager = BrowserManager()
    return _manager


def shutdown_browser():
    """Shut down the global browser manager (called at pipeline end)."""
    global _manager
    if _manager:
        _manager.stop()
        _manager = None