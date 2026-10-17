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


def test_ats_provider_recognition():
 from app import ats_provider_for_url
 assert ats_provider_for_url("https://jobs.lever.co/acme/123")=="lever"
 assert ats_provider_for_url("https://jobs.ashbyhq.com/acme/123")=="ashby"
 assert ats_provider_for_url("https://example.com/job")=="external"


def test_ats_readiness_does_not_claim_submission():
 r=client.post("/api/application/packet",json={"company":"Example","job_title":"Engineer","apply_url":"https://jobs.lever.co/example/123"})
 assert r.status_code==200
 assert r.json()["ats_readiness"]["verified_form_schema"] is False
 assert r.json()["ats_readiness"]["submission_supported"] is False


def test_health_reflects_optional_cloud_sync():
    payload=client.get("/api/health").json()
    assert payload["version"]=="0.4.1"
    assert "optional authenticated cloud sync" in payload["storage"]


def test_invalid_resume_upload_too_large():
    payload=b"P"*(4*1024*1024+1)
    result=client.post("/api/resume/analyze",files={"file":("resume.txt",payload,"text/plain")})
    assert result.status_code==413


def test_recommendation_rejects_invalid_experience_limit():
    payload={"resume_text":"Python machine learning engineering with development experience and practice.", "jobs":[{"title":"Engineer"}],"max_experience":-1}
    assert client.post("/api/resume/recommend",json=payload).status_code==422

def test_job_description_normalization():
 from app import normalized
 job={"id":1,"title":"ML Engineer","content":"<p>Python &amp; <strong>PyTorch</strong> required</p>","absolute_url":"https://example.com/a","location":{"name":"Coimbatore"}}
 result=normalized("greenhouse",job,"acme")
 assert result["description"]=="Python & PyTorch required"
 assert result["location"]=="Coimbatore"

def test_remote_metadata_not_guessed():
 from app import normalized
 remote=normalized("remotive",{"id":2,"title":"Engineer","url":"https://example.com/remote","description":"<div>Python</div>"})
 local=normalized("arbeitnow",{"slug":"job-3","title":"Engineer","url":"https://example.com/local","remote":False})
 assert remote["remote"] is True
 assert local["remote"] is False
 assert remote["description"]=="Python"
