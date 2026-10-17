"""Deterministic pre-submission review for candidate-approved applications.

Never calls external ATS endpoints or claims an employer application was sent.
"""
from urllib.parse import urlsplit
from job_discovery_watch import canonical_url

REQUIRED_FIELDS=("full_name","email","phone","resume_attached")
def review_application(data):
    candidate=data["candidate"]
    missing=[]
    for field in REQUIRED_FIELDS:
        value=candidate.get(field)
        if field=="resume_attached":
            if value is not True: missing.append(field)
        elif not isinstance(value,str) or not value.strip():
            missing.append(field)
    employer_questions=data.get("employer_questions",[])
    unanswered=[q["key"] for q in employer_questions if q.get("required",False) and not str(q.get("answer") or "").strip()]
    url=data["apply_url"]
    parsed=urlsplit(url)
    valid_link=bool(canonical_url(url) and not parsed.username and not parsed.password)
    consent=data.get("candidate_approved") is True
    blockers=[]
    if not valid_link: blockers.append("Invalid HTTPS application link")
    if missing: blockers.append("Missing required candidate details")
    if unanswered: blockers.append("Unanswered required employer questions")
    if not consent: blockers.append("Candidate approval is required")
    return {"ready_for_manual_submission":not blockers,
            "blockers":blockers,"missing_candidate_fields":missing,
            "unanswered_questions":unanswered,
            "submission_status":"NOT_SUBMITTED",
            "submission_supported":False,
            "next_action":"Review employer website and submit manually" if not blockers else "Resolve blockers before visiting the employer application form"}
