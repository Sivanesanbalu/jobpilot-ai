from fastapi.testclient import TestClient
from app import app

client=TestClient(app)
def test_draft_uses_only_verified_matching_skills():
    body={"candidate":{"full_name":"Test Applicant","verified_skills":["Python","PyTorch","UnrelatedSkill"]},
          "job":{"title":"AI Engineer","company":"Example","description":"Python and PyTorch experience"},
          "employer_questions":[{"key":"work_authorization","required":True}]}
    response=client.post("/api/application/draft",json=body)
    assert response.status_code==200
    draft=response.json()
    assert draft["verified_skill_matches"]==["Python","PyTorch"]
    assert "UnrelatedSkill" not in draft["draft"]
    assert draft["questions_needing_candidate_input"][0]["key"]=="work_authorization"
    assert draft["submission_status"]=="NOT_SUBMITTED"
    assert draft["requires_candidate_review"] is True

def test_draft_does_not_invent_skills():
    result=client.post("/api/application/draft",json={
        "candidate":{"verified_skills":[]},
        "job":{"title":"Developer","company":"Example","description":"Python required"}}).json()
    assert "Python" not in result["draft"]
    assert result["verified_skill_matches"]==[]
