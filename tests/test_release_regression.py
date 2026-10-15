from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_home_renders_and_account_controls_present():
    response = client.get("/")
    assert response.status_code == 200
    assert "JobPilot AI" in response.text
    assert 'id="signInBtn"' in response.text
    assert 'id="accountPanel"' in response.text

def test_security_headers_present():
    response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"

def test_application_draft_never_submits():
    response = client.post("/api/application/packet", json={
        "company": "Example", "job_title": "AI Engineer",
        "apply_url": "https://jobs.ashbyhq.com/example/123",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["submission_status"] == "NOT_SUBMITTED"
    assert payload["ats_readiness"]["submission_supported"] is False
    assert payload["ats_readiness"]["verified_form_schema"] is False

def test_private_url_rejected_without_fetching():
    response = client.post("/api/application/packet", json={
        "company": "Example", "job_title": "Engineer",
        "apply_url": "https://127.0.0.1/private",
    })
    assert response.status_code == 422


def test_home_uses_dashboard_file():
    from pathlib import Path
    expected = Path(__file__).resolve().parents[1].joinpath("dashboard.html").read_text(encoding="utf-8")
    assert client.get("/").text == expected


def test_account_cache_isolation_hooks_present():
    html = client.get("/").text
    assert "function isolateAccount(nextId)" in html
    assert "jp_account_owner" in html
    assert "if(user)isolateAccount(user.id)" in html
