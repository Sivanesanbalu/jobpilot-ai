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
