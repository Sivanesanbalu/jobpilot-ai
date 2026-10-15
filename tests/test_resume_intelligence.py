from fastapi.testclient import TestClient
from app import app
from resume_intelligence import extract_skills, match_resume_to_job

client = TestClient(app)

def test_skill_alias_and_boundaries():
    assert "rag" in extract_skills("Retrieval-Augmented Generation and Python")
    assert "sql" not in extract_skills("NoSQL data store")
    assert "react" in extract_skills("Built React.js frontends")

def test_match_reports_missing_skills():
    result = match_resume_to_job("Python and PyTorch", "ML Engineer", "Python PyTorch Docker")
    assert result["score"] == 67
    assert result["matched_skills"] == ["python", "pytorch"]
    assert result["missing_skills"] == ["docker"]

def test_unscorable_job_does_not_claim_perfect_match():
    result = match_resume_to_job("Python", "Engineer", "Communication skills")
    assert result["score"] is None

def test_match_api_returns_explainable_result():
    r=client.post("/api/resume/match",json={"resume_text":"Python PyTorch build and deploy machine learning systems in production.","job_title":"ML Engineer","job_description":"Python PyTorch Docker"})
    assert r.status_code == 200
    assert "docker" in r.json()["missing_skills"]
    assert r.json()["requires_manual_review"] is True

def test_match_api_rejects_too_short_resume():
    r=client.post("/api/resume/match",json={"resume_text":"Python","job_title":"Engineer"})
    assert r.status_code == 422
