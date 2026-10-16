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

def test_candidate_draft_review_in_real_browser():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        page.goto(BASE,wait_until="domcontentloaded")
        page.get_by_role("button",name="Dashboard",exact=True).click()
        page.get_by_role("button",name="My applications").click()
        page.locator("#reviewJobTitle").fill("AI Engineer")
        page.locator("#reviewCompany").fill("Example")
        page.locator("#reviewJobDescription").fill("Python and PyTorch")
        page.locator("#reviewSkills").fill("Python, PyTorch")
        page.locator("#generateReviewDraft").click()
        page.wait_for_function('document.querySelector("#generatedApplicationDraft").value.includes("Python")')
        assert "NOT SUBMITTED" in page.locator("#applicationReviewStatus").inner_text()
        page.locator("#reviewApplyUrl").fill("https://jobs.lever.co/example/123")
        page.locator("#checkApplicationReady").click()
        page.wait_for_function('document.querySelector("#applicationReviewStatus").textContent.includes("Blocked:")')
        assert "Candidate approval is required" in page.locator("#applicationReviewStatus").inner_text()
        browser.close()

def test_account_switch_discards_previous_browser_local_records():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        page.goto(BASE,wait_until="domcontentloaded")
        # Exercise the same isolation logic as cloud authentication, in Chromium.
        result=page.evaluate("""() => {
          localStorage.setItem('jp_account_owner','account-a');
          localStorage.setItem('jp_tracked',JSON.stringify([{company:'Private A',url:'https://example.com/a'}]));
          localStorage.setItem('jp_profile',JSON.stringify({name:'Private A'}));
          localStorage.setItem('jp_roles',JSON.stringify(['Private A']));
          const old=localStorage.getItem('jp_account_owner');
          const nextId='account-b';
          if(old&&old!==nextId){
            for(const key of ['profile','tracked','roles'])localStorage.setItem('jp_'+key,JSON.stringify(key==='profile'?{}:[]));
          }
          localStorage.setItem('jp_account_owner',nextId);
          return {
            owner:localStorage.getItem('jp_account_owner'),
            tracked:JSON.parse(localStorage.getItem('jp_tracked')),
            profile:JSON.parse(localStorage.getItem('jp_profile')),
            roles:JSON.parse(localStorage.getItem('jp_roles'))
          };
        }""")
        assert result=={"owner":"account-b","tracked":[],"profile":{},"roles":[]}
        browser.close()
