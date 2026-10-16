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
          const source=[...document.scripts].map(x=>x.textContent).find(x=>x.includes('function isolateAccount(nextId)'));
          const functionSource=source.match(/function isolateAccount\\(nextId\\)\\{[^\\n]+\\}/)[0];
          const actual=Function('setLocal',functionSource+'; return isolateAccount')(
            (key,value)=>localStorage.setItem('jp_'+key,JSON.stringify(value))
          );
          actual('account-b');
          return {
            owner:localStorage.getItem('jp_account_owner'),
            tracked:JSON.parse(localStorage.getItem('jp_tracked')),
            profile:JSON.parse(localStorage.getItem('jp_profile')),
            roles:JSON.parse(localStorage.getItem('jp_roles'))
          };
        }""")
        assert result=={"owner":"account-b","tracked":[],"profile":{},"roles":[]}
        browser.close()

def test_stale_cloud_history_response_cannot_render_after_account_switch():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        page.goto(BASE,wait_until="domcontentloaded")
        result=page.evaluate("""async () => {
          const source=[...document.scripts].map(s=>s.textContent).find(s=>s.includes('async function cloudStatusHistory()'));
          const body=source.match(/async function cloudStatusHistory\\(\\)\\{[^\\n]+\\}/)[0];
          let resolveFetch;
          const delayed=new Promise(resolve=>resolveFetch=resolve);
          let current={id:'account-a'};
          const root=document.querySelector('#cloudStatusHistory');
          const fn=Function('document','getUser','sb',body.replaceAll('user.id','getUser().id').replaceAll('!user','!getUser()')+'; return cloudStatusHistory')(
            document,()=>current,{
              from:()=>({select:()=>({eq:()=>({order:()=>({limit:()=>delayed})})})})
            }
          );
          const pending=fn();
          current={id:'account-b'};
          resolveFetch({data:[{apply_url:'https://private.example/a',current_status:'submitted',changed_at:new Date().toISOString()}],error:null});
          await pending;
          return root.textContent.includes('private.example');
        }""")
        assert result is False
        browser.close()

def test_stale_cloud_draft_buttons_are_blocked_after_account_switch():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        page.goto(BASE,wait_until="domcontentloaded")
        outcome=page.evaluate("""() => {
          const source=[...document.scripts].map(s=>s.textContent).find(s=>s.includes('async function cloudLoadApplicationDrafts()'));
          const start=source.indexOf('async function cloudLoadApplicationDrafts()');
          const end=source.indexOf('function draftStorageKey()',start);
          const body=source.slice(start,end);
          const guarded=['restore.onclick=()=>{if(!user||user.id!==requestOwner)return;',
            'remove.onclick=async()=>{if(!user||user.id!==requestOwner)return;',
            'track.onclick=()=>{if(!user||user.id!==requestOwner)return;'];
          return guarded.every(x=>body.includes(x));
        }""")
        assert outcome is True
        browser.close()

def test_stale_cloud_draft_restore_click_does_not_change_form():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        page.goto(BASE,wait_until="domcontentloaded")
        result=page.evaluate("""async () => {
          const source=[...document.scripts].map(s=>s.textContent).find(s=>s.includes('async function cloudLoadApplicationDrafts()'));
          const body=source.slice(source.indexOf('async function cloudLoadApplicationDrafts()'),source.indexOf('function draftStorageKey()'));
          const start=body.indexOf('restore.onclick=()=>');
          const end=body.indexOf(';remove.className',start);
          const handler=body.slice(start,end);
          let user={id:'account-b'};
          const requestOwner='account-a';
          const item={draft_text:'PRIVATE ACCOUNT A',job_title:'Private',company:'Private Co',apply_url:'https://example.com/private'};
          const restore={};
          const $=id=>document.getElementById(id);
          document.getElementById('generatedApplicationDraft').value='CURRENT USER';
          Function('restore','getUser','requestOwner','item','$',handler.replaceAll('!user','!getUser()').replaceAll('user.id','getUser().id'))(restore,()=>user,requestOwner,item,$);
          restore.onclick();
          return document.getElementById('generatedApplicationDraft').value;
        }""")
        assert result=="CURRENT USER"
        browser.close()

def test_stale_draft_delete_and_track_handlers_do_not_mutate_state():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        page.goto(BASE,wait_until="domcontentloaded")
        result=page.evaluate("""async () => {
          const source=[...document.scripts].map(s=>s.textContent).find(s=>s.includes('async function cloudLoadApplicationDrafts()'));
          const body=source.slice(source.indexOf('async function cloudLoadApplicationDrafts()'),source.indexOf('function draftStorageKey()'));
          const removeSource=body.slice(body.indexOf('remove.onclick=async()=>'),body.indexOf(';const approve=',body.indexOf('remove.onclick=async()=>')));
          const trackSource=body.slice(body.indexOf('track.onclick=()=>'),body.indexOf(';line.append(',body.indexOf('track.onclick=()=>')));
          const remove={}, track={}, item={id:'private-a',apply_url:'https://example.com/private',job_title:'Private',company:'Private'};
          let user={id:'account-b'}, writes=0, confirmations=0;
          const requestOwner='account-a';
          const fakeDb={from:()=>{writes++;throw Error('stale delete requested')}};
          const $=id=>document.getElementById(id);
          const confirm=()=>{confirmations++;return true};
          Function('remove','getUser','requestOwner','item','sb','$','confirm','cloudLoadApplicationDrafts',removeSource.replaceAll('!user','!getUser()').replaceAll('user.id','getUser().id'))(remove,()=>user,requestOwner,item,fakeDb,$,confirm,async()=>{});
          Function('track','getUser','requestOwner','item','$',trackSource.replaceAll('!user','!getUser()').replaceAll('user.id','getUser().id'))(track,()=>user,requestOwner,item,$);
          const initial=JSON.stringify([{company:'Current account',url:'https://example.com/current'}]);
          localStorage.setItem('jp_tracked',initial);
          await remove.onclick();
          track.onclick();
          return {writes,confirmations,unchanged:localStorage.getItem('jp_tracked')===initial};
        }""")
        assert result=={"writes":0,"confirmations":0,"unchanged":True}
        browser.close()
