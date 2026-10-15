from fastapi.testclient import TestClient
from app import app
from job_discovery_watch import canonical_url, new_job_matches

def test_normalizes_tracking_fragment():
    assert canonical_url("https://EXAMPLE.com/jobs/1/#details") == "https://example.com/jobs/1"
    assert canonical_url("http://example.com/jobs/1") == ""

def test_detects_only_unseen_jobs():
    jobs=[{"url":"https://example.com/a/","title":"A"},{"url":"https://example.com/b","title":"B"},{"url":"https://example.com/b","title":"Duplicate"}]
    result=new_job_matches(["https://example.com/a"],jobs)
    assert len(result)==1
    assert result[0]["title"]=="B"

def test_changes_api_no_notifications():
    r=TestClient(app).post("/api/jobs/changes",json={"known_urls":["https://example.com/a"],"jobs":[{"title":"ML Engineer","url":"https://example.com/b"}]})
    assert r.status_code==200
    assert r.json()["count"]==1
    assert r.json()["notifications_sent"] is False
