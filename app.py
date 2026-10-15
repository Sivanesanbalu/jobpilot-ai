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
    return "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>JobPilot AI</title><style>body{margin:0;background:#0b1120;color:#edf3ff;font:16px system-ui}main{max-width:960px;margin:40px auto;padding:24px}h1{font-size:36px}section{background:#151f35;border:1px solid #32405a;border-radius:16px;padding:22px;margin:20px 0}input,select,button{padding:12px;border-radius:9px;border:1px solid #435674;font:inherit}input,select{background:#10182b;color:white}button{background:#6b5cff;color:white;cursor:pointer}form{display:flex;flex-wrap:wrap;gap:10px}.job{padding:14px;border-top:1px solid #35445b}.job a{color:#a6b7ff}small{color:#b4c2da}</style></head><body><main><h1>🚀 JobPilot AI</h1><p>Discover publicly posted jobs across Greenhouse, Lever, Ashby and SmartRecruiters.</p><section><h2>Find company jobs</h2><form id=\"form\"><select id=\"provider\"><option>greenhouse</option><option>lever</option><option>ashby</option><option>smartrecruiters</option></select><input id=\"company\" required placeholder=\"Company board slug\" maxlength=\"120\"><button>Fetch jobs</button></form><p><small>Find the exact slug on the company's official career board. Listings are public; applications open on employer sites. This version does not store resumes or submit applications.</small></p></section><section><h2>Results</h2><div id=\"results\">Add a company board to begin.</div></section></main><script>document.querySelector('#form').addEventListener('submit',async e=>{e.preventDefault();const out=document.querySelector('#results');out.textContent='Loading jobs…';try{let provider=document.querySelector('#provider').value,slug=document.querySelector('#company').value;let r=await fetch('/api/jobs/'+encodeURIComponent(provider)+'/'+encodeURIComponent(slug));let data=await r.json();if(!r.ok)throw Error(data.detail||'Failed to fetch jobs');out.replaceChildren();const count=document.createElement('p');count.textContent=data.count+' jobs found';out.append(count);for(const j of data.jobs){const d=document.createElement('div');d.className='job';const a=document.createElement('a');a.href=j.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=j.title||'Untitled role';d.append(a);const p=document.createElement('p');p.textContent=j.location||'Location not specified';d.append(p);out.append(d)}}catch(err){out.textContent='Error: '+err.message}})</script></body></html>"
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
