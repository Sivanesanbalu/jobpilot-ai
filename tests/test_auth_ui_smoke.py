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
