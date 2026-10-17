from fastapi.testclient import TestClient
from app import app

client=TestClient(app)
def data(**extra):
    payload={"apply_url":"https://jobs.lever.co/example/123",
      "candidate":{"full_name":"Applicant","email":"applicant@example.com","phone":"1234567890","resume_attached":True},
      "employer_questions":[{"key":"work_eligibility","required":True,"answer":"Eligible"}],
      "candidate_approved":True}
    payload.update(extra)
    return payload

def test_ready_application_never_claims_submission():
    response=client.post("/api/application/review",json=data())
    assert response.status_code==200
    result=response.json()
    assert result["ready_for_manual_submission"] is True
    assert result["submission_status"]=="NOT_SUBMITTED"
    assert result["submission_supported"] is False

def test_missing_consent_blocks_readiness():
    result=client.post("/api/application/review",json=data(candidate_approved=False)).json()
    assert result["ready_for_manual_submission"] is False
    assert "Candidate approval is required" in result["blockers"]

def test_missing_resume_and_answer_are_reported():
    result=client.post("/api/application/review",json=data(candidate={"full_name":"Applicant","email":"applicant@example.com","phone":"1234567890","resume_attached":False},employer_questions=[{"key":"notice_period","required":True}])).json()
    assert result["missing_candidate_fields"]==["resume_attached"]
    assert result["unanswered_questions"]==["notice_period"]

def test_non_https_link_is_blocked():
    result=client.post("/api/application/review",json=data(apply_url="http://example.com/apply")).json()
    assert result["ready_for_manual_submission"] is False
