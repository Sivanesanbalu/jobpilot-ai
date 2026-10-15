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
