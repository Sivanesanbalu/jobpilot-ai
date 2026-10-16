"""Fact-grounded application drafting. Never fabricates achievements or submits."""
import re

def make_application_draft(candidate, job, questions):
    name=(candidate.get("full_name") or "").strip()
    skills=[s.strip() for s in candidate.get("verified_skills",[]) if isinstance(s,str) and s.strip()]
    skills=list(dict.fromkeys(skills))[:8]
    title=(job.get("title") or "").strip()
    company=(job.get("company") or "").strip()
    requirements=(job.get("description") or "").lower()
    matched=[s for s in skills if re.search(r"(?<!\w)"+re.escape(s.lower())+r"(?!\w)",requirements)]
    intro=f"I am interested in the {title} role at {company}."
    if matched: intro+=" My relevant skills include "+", ".join(matched)+"."
    intro+=" I would welcome the opportunity to discuss my fit for this role."
    pending=[{"key":q["key"],"reason":"Requires candidate-provided information"} for q in questions if q.get("required") and not str(q.get("answer") or "").strip()]
    return {"draft":intro,"verified_skill_matches":matched,
            "questions_needing_candidate_input":pending,
            "facts_source":"candidate_verified_skills_only",
            "submission_status":"NOT_SUBMITTED","requires_candidate_review":True}
