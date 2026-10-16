from pathlib import Path
from playwright.sync_api import sync_playwright

BASE="http://127.0.0.1:8765"

def test_dashboard_browser_load_and_review_controls():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.goto(BASE,wait_until="domcontentloaded")
        assert page.title().startswith("JobPilot AI")
        assert page.locator("#applicationReviewCard").count()==1
        assert page.locator("#reviewApproved").count()==1
        assert page.locator("#cloudLoadDraftsBtn").count()==1
        assert page.locator("#tracked").count()==1
        # The cloud module can fail gracefully without project credentials.
        assert not [e for e in errors if "SyntaxError" in e]
        browser.close()
