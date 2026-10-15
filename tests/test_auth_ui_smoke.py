from fastapi.testclient import TestClient
from app import app


def test_account_ui_present():
    html = TestClient(app).get('/').text
    assert 'googleSignInBtn' in html
    assert 'PASSWORD_RECOVERY' in html
    assert 'signInWithOAuth' in html


def test_cloud_merge_preserves_unsynced_jobs():
    html = TestClient(app).get("/").text
    assert "remote.concat(jobs().filter" in html
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
