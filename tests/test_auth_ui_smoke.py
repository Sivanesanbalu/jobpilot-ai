from fastapi.testclient import TestClient
from app import app


def test_account_ui_present():
    html = TestClient(app).get('/').text
    assert 'googleSignInBtn' in html
    assert 'PASSWORD_RECOVERY' in html
    assert 'signInWithOAuth' in html
