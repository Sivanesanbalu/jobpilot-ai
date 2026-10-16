from fastapi.testclient import TestClient
from app import app


def test_account_ui_present():
    html = TestClient(app).get('/').text
    assert 'googleSignInBtn' in html
    assert 'PASSWORD_RECOVERY' in html
    assert 'signInWithOAuth' in html


def test_cloud_merge_preserves_unsynced_jobs():
    html = TestClient(app).get("/").text
    assert "setLocal(\"tracked\",mergeApplicationRecords(remote,jobs()))" in html
    assert "if(changed){syncReady=false" in html


def test_autosync_waits_for_successful_initial_save():
    html = TestClient(app).get("/").text
    assert 'if(await sync("profile"))syncReady=true' in html
    assert 'if(await sync("tracked"))syncReady=true' in html


def test_confirmed_submission_not_overwritten_by_unsent_local_data():
    html = TestClient(app).get("/").text
    assert "existing.data.submitted_at&&!payload.submitted_at" in html


def test_empty_job_sync_is_not_marked_successful():
    html = TestClient(app).get("/").text
    assert "No saved applications to sync" in html
    assert "Saved jobs can be synced to your account" in html

def test_ranked_jobs_render_filtered_and_deduplicated_response():
    html = TestClient(app).get("/").text
    assert 'results=data.jobs.map(j=>buckets.get(' in html
    assert 'filter(Boolean)' in html
    assert 'unique listings matching your selected preferences' in html

def test_notification_inbox_requires_signed_in_user():
    html=TestClient(app).get("/").text
    assert 'if(!user||!sb)' in html
    assert 'sb.from("job_notifications").select(' in html
    assert '.eq("user_id",user.id)' in html
    assert 'id="loadNotificationsBtn"' in html
    assert 'Mark read' in html

def test_application_review_dashboard_routes_and_approval_control():
    html = TestClient(app).get("/").text
    assert 'id="applicationReviewCard"' in html
    assert 'id="reviewApproved"' in html
    assert 'id="generatedApplicationDraft"' in html
    assert '"/api/application/draft"' in html
    assert '"/api/application/review"' in html
    assert 'candidate_approved:approved' in html
    assert 'NOT SUBMITTED' in html
    assert 'line.indexOf("=")' in html

def test_application_draft_history_is_local_and_not_submitted():
    html=TestClient(app).get("/").text
    assert 'id="saveApplicationDraftBtn"' in html
    assert 'id="showApplicationDraftsBtn"' in html
    assert 'function draftStorageKey()' in html
    assert 'function readDrafts()' in html
    assert 'submission_status:"NOT_SUBMITTED"' in html
    assert 'Review again before approval' in html
    assert 'localStorage.setItem(draftStorageKey()' in html

def test_tracker_manual_status_history_and_submission_guard():
    html = TestClient(app).get("/").text
    assert 'function updateTrackedStatus(job,next)' in html
    assert 'next==="Applied"&&!job.submitted_at' in html
    assert 'source:"candidate_manual_update"' in html
    assert 'function trackerSummary()' in html
    assert "heading.textContent='Status history (" in html
    assert "updateTrackedStatus(j,'Applied')" in html

def test_application_tracker_cloud_merge_and_duplicate_guards():
    html=TestClient(app).get("/").text
    assert 'function applicationUrlKey(url)' in html
    assert 'function mergeApplicationRecords(remote,local)' in html
    assert 'setLocal("tracked",mergeApplicationRecords(remote,jobs()))' in html
    assert 'for(const j of mergeApplicationRecords([],jobs()))' in html
    assert 'const confirmed=[previous,j].find(x=>x.submitted_at)' in html
    assert 'p.pathname.replace(new RegExp("/+$"),"")' in html
    assert '||"/")+p.search' in html

def test_tracker_funnel_analytics_has_safe_zero_denominator():
    html=TestClient(app).get("/").text
    assert "function trackerConversionMetrics()" in html
    assert "den?Math.round(1000*num/den)/10:0" in html
    assert "counts.Applied+counts.Interview+counts.Offer+counts.Rejected" in html
    assert "analytics.id='trackerConversionMetrics'" in html
    assert "Interview: " in html and "Offers: " in html


def test_merge_prefers_latest_confirmed_submission_timestamp():
    html=TestClient(app).get("/").text
    assert 'filter(x=>x.submitted_at).sort((a,b)=>String(b.submitted_at).localeCompare(String(a.submitted_at)))' in html
    assert 'const chosen=confirmed||j' in html
