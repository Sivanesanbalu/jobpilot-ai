from fastapi.testclient import TestClient
from app import app

client=TestClient(app)
def test_health():
 assert client.get("/api/health").status_code==200
def test_match_scoring():
 resp=client.post("/api/match/score",json={"skills":["Python","PyTorch"],"preferred_roles":["AI Engineer"],"job_title":"AI Engineer","job_description":"Python PyTorch"})
 assert resp.status_code==200
 assert resp.json()["score"]>0
def test_billing_not_active():
 result=client.get("/api/plans").json()
 assert result["billing_enabled"] is False
def test_invalid_company_slug():
 assert client.get("/api/jobs/lever/@@@").status_code==400


def test_missing_job_title_rejected():
 result=client.post("/api/match/score",json={"skills":["Python"]})
 assert result.status_code==422

def test_invalid_resume_format_rejected():
 response=client.post("/api/resume/analyze",files={"file":("test.exe",b"test","application/octet-stream")})
 assert response.status_code==415

def test_public_configuration_has_no_secret_key():
 keys=set(client.get("/api/public-config").json())
 assert keys=={"url","publishable_key"}

def test_application_packet_is_draft_only():
 r=client.post("/api/application/packet",json={"company":"Example Co","job_title":"AI Engineer","apply_url":"https://example.com/jobs/123","full_name":"Applicant"})
 assert r.status_code==200
 assert r.json()["submission_status"]=="NOT_SUBMITTED"
 assert "email" in r.json()["missing_fields"]

def test_application_packet_rejects_insecure_url():
 r=client.post("/api/application/packet",json={"company":"Example Co","job_title":"AI Engineer","apply_url":"http://example.com/apply"})
 assert r.status_code==422
