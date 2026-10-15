"""Deterministic, explainable resume-to-job matching without storing resume text."""
import re

SKILLS = {
    "python": ("python",), "pytorch": ("pytorch",), "tensorflow": ("tensorflow",),
    "machine learning": ("machine learning",), "deep learning": ("deep learning",),
    "rag": ("rag", "retrieval augmented generation", "retrieval-augmented generation"),
    "llm": ("llm", "large language model", "large language models"),
    "transformers": ("transformers", "hugging face"),
    "sql": ("sql", "postgresql", "mysql"), "react": ("react", "react.js"),
    "next.js": ("next.js", "nextjs"), "typescript": ("typescript",),
    "javascript": ("javascript",), "fastapi": ("fastapi",),
    "docker": ("docker",), "aws": ("aws", "amazon web services"),
    "opencv": ("opencv",), "yolo": ("yolo", "yolov8", "yolov11"),
    "scikit-learn": ("scikit-learn", "sklearn"), "nlp": ("nlp", "natural language processing"),
}

def _found(text, names):
    return any(re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.I) for name in names)

def extract_skills(text):
    return sorted(key for key, names in SKILLS.items() if _found(text or "", names))

def match_resume_to_job(resume_text, job_title, job_description):
    """Keyword relevance heuristic, not a hiring probability or ATS assessment."""
    resume_skills = set(extract_skills(resume_text))
    requested = set(extract_skills((job_title or "") + " " + (job_description or "")))
    matched = sorted(requested & resume_skills)
    missing = sorted(requested - resume_skills)
    score = round(100 * len(matched) / len(requested)) if requested else None
    return {"score": score, "matched_skills": matched, "missing_skills": missing,
            "resume_skills": sorted(resume_skills), "job_skills": sorted(requested),
            "method": "skill_keyword_overlap", "requires_manual_review": True,
            "disclaimer": "This is a keyword relevance estimate, not an ATS score or hiring prediction. No resume data is retained."}

def rank_jobs(resume_text, jobs, preferred_location="", remote_only=False, max_experience=None):
    """Skill relevance first, with transparent preference filtering and no inferred experience claims."""
    output=[]
    seen=set()
    location=(preferred_location or "").strip().casefold()
    for job in jobs[:100]:
        url=(job.get("url") or "").strip()
        identity=("url",url.rstrip("/").casefold()) if url else ("role",(job.get("company") or "").strip().casefold(),(job.get("title") or "").strip().casefold(),(job.get("location") or "").strip().casefold())
        if identity in seen:
            continue
        seen.add(identity)
        title=job.get("title","")
        description=job.get("description","")
        job_location=(job.get("location") or "").casefold()
        remote=bool(job.get("remote",False)) or "remote" in job_location
        years=job.get("min_experience")
        if remote_only and not remote:
            continue
        if location and location not in job_location and not remote:
            continue
        if max_experience is not None and years is not None and years>max_experience:
            continue
        result=match_resume_to_job(resume_text,title,description)
        output.append({"title":title,"company":job.get("company",""),"url":url,
                       "location":job.get("location",""),"remote":remote,
                       "score":result["score"],"matched_skills":result["matched_skills"],
                       "missing_skills":result["missing_skills"],"review_required":True,
                       "explanation":("Matched "+str(len(result["matched_skills"]))+" of "+str(len(result["job_skills"]))+" recognized required skills." if result["score"] is not None else "No recognized technical requirements; ranking unavailable.")})
    return sorted(output,key=lambda x:(x["score"] is None,-(x["score"] or 0),-len(x["matched_skills"])))
