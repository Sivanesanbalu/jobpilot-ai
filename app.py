from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import httpx
app = FastAPI(title="JobPilot AI", version="0.2.0")
PROVIDERS = {
    "greenhouse": ("https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true", "jobs"),
    "lever": ("https://api.lever.co/v0/postings/{slug}?mode=json", None),
    "ashby": ("https://api.ashbyhq.com/posting-api/job-board/{slug}", "jobs"),
    "smartrecruiters": ("https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100", "content")
}
@app.get("/", response_class=HTMLResponse)
def home():
    return Path(__file__).resolve().parents[1].joinpath("index.html").read_text()
@app.get("/api/health")
def health():
    return {"ok":True, "mode":"read-only", "persistent_storage":False}
@app.get("/api/jobs/{provider}/{slug}")
async def jobs(provider: str, slug: str):
    import re
    if provider not in PROVIDERS or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,120}",slug):
        raise HTTPException(400,"Invalid board")
    url,key=PROVIDERS[provider]
    try:
        async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
            resp=await client.get(url.format(slug=slug))
            resp.raise_for_status()
            body=resp.json()
    except (httpx.HTTPError,ValueError):
        raise HTTPException(502,"Job board not available")
    raw=body if key is None else body.get(key,[])
    if not isinstance(raw,list): raise HTTPException(502,"Unexpected response")
    result=[]
    for j in raw[:300]:
        if not isinstance(j,dict): continue
        if provider=="greenhouse":
            result.append(dict(id=str(j.get("id")),title=j.get("title",""),location=(j.get("location") or {}).get("name",""),url=j.get("absolute_url","")))
        elif provider=="lever":
            result.append(dict(id=str(j.get("id")),title=j.get("text",""),location=(j.get("categories") or {}).get("location",""),url=j.get("hostedUrl","")))
        elif provider=="ashby":
            result.append(dict(id=str(j.get("id")),title=j.get("title",""),location=j.get("location",""),url=j.get("applyUrl") or j.get("jobUrl","")))
        else:
            result.append(dict(id=str(j.get("id")),title=j.get("name",""),location=(j.get("location") or {}).get("city",""),url=j.get("ref","")))
    return {"provider":provider,"company":slug,"count":len(result),"jobs":[r for r in result if str(r["url"]).startswith("https://")]}
