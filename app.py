from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from pathlib import Path
from io import BytesIO
import asyncio, re, httpx
from html import unescape
from pypdf import PdfReader

app=FastAPI(title="JobPilot AI",version="0.4.1")
BOARDS={
 "greenhouse":("https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true","jobs"),
 "lever":("https://api.lever.co/v0/postings/{slug}?mode=json",None),
 "ashby":("https://api.ashbyhq.com/posting-api/job-board/{slug}","jobs"),
 "smartrecruiters":("https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100","content")
}
ROLE_RULES={
 "AI / Machine Learning Engineer":["machine learning","pytorch","tensorflow","scikit-learn","ml engineer","deep learning"],
 "Generative AI / LLM Engineer":["llm","rag","transformers","langchain","fine-tun","prompt engineering","generative ai"],
 "Data Scientist":["data analysis","pandas","statistics","sql","data science"],
 "Frontend Developer":["react","next.js","typescript","javascript","tailwind","frontend"],
 "Backend Developer":["fastapi","django","flask","node.js","postgresql","backend"],
 "Computer Vision Engineer":["opencv","yolo","object detection","computer vision"],
 "DevOps / MLOps Engineer":["docker","kubernetes","mlops","ci/cd","aws","deployment"],
 "QA / Test Automation":["selenium","playwright","testing","qa engineer","test automation"],
 "Product / Business Analyst":["business analyst","product management","stakeholder","requirements"]
}
@app.get("/",response_class=HTMLResponse)
def home():
 return Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8")
@app.get("/api/health")
def health():
 return {"ok":True,"version":"0.4.1","storage":"browser plus optional authenticated cloud sync","applications":"manual approval"}

async def parse_resume_text(file:UploadFile):
 name=(file.filename or "").lower()
 if not name.endswith((".pdf",".txt")): raise HTTPException(415,"Upload a PDF or TXT resume.")
 raw=await file.read(4*1024*1024+1)
 if len(raw)>4*1024*1024: raise HTTPException(413,"Max resume size 4 MB")
 try:
  if name.endswith(".pdf"):
   reader=PdfReader(BytesIO(raw))
   if len(reader.pages)>25: raise HTTPException(413,"Max 25 pages")
   content=" ".join(page.extract_text() or "" for page in reader.pages)
  else: content=raw.decode("utf-8",errors="replace")
 except HTTPException: raise
 except Exception: raise HTTPException(422,"Could not read resume. Scanned PDFs need OCR, not available yet.")
 if len(content.strip())<40: raise HTTPException(422,"Resume contains too little extractable text")
 return content

@app.post("/api/resume/analyze")
async def analyze_resume(file:UploadFile=File(...)):
 content=await parse_resume_text(file)
 lower=content.lower()
 scores=[]
 for role,words in ROLE_RULES.items():
  matched=[w for w in words if w in lower]
  scores.append({"role":role,"score":len(matched),"skills":matched})
 scores=sorted(scores,key=lambda a:-a["score"])
 found=sorted({x for r in scores for x in r["skills"]})
 return {"suggested_roles":[s for s in scores if s["score"]>0][:5] or scores[:3],"skills":found[:30],"extracted_characters":len(content),"note":"Resume parsed in memory and not stored on the server. Review recommendations before using."}

def plain_description(value):
 if not isinstance(value,str): return ""
 return re.sub(r"\s+"," ",unescape(re.sub(r"<[^>]+>"," ",value))).strip()[:10000]

def normalized(provider,j,slug=""):
 if provider=="greenhouse": return {"id":str(j.get("id")),"title":j.get("title",""),"company":slug,"location":(j.get("location") or {}).get("name",""),"url":j.get("absolute_url",""),"source":provider,"description":plain_description(j.get("content",""))}
 if provider=="lever": return {"id":str(j.get("id")),"title":j.get("text",""),"company":slug,"location":(j.get("categories") or {}).get("location",""),"url":j.get("hostedUrl",""),"source":provider,"description":plain_description(j.get("descriptionPlain") or j.get("description",""))}
 if provider=="ashby": return {"id":str(j.get("id")),"title":j.get("title",""),"company":slug,"location":j.get("location",""),"url":j.get("applyUrl") or j.get("jobUrl",""),"source":provider,"description":plain_description(j.get("descriptionPlain") or j.get("descriptionHtml","")),"remote":bool(j.get("isRemote",False))}
 if provider=="smartrecruiters": return {"id":str(j.get("id")),"title":j.get("name",""),"company":slug,"location":(j.get("location") or {}).get("city",""),"url":j.get("ref",""),"source":provider,"description":plain_description(j.get("jobAd",""))}
 if provider=="remotive": return {"id":str(j.get("id")),"title":j.get("title",""),"company":j.get("company_name",""),"location":j.get("candidate_required_location",""),"url":j.get("url",""),"source":provider,"description":plain_description(j.get("description","")),"remote":True}
 if provider=="arbeitnow": return {"id":str(j.get("slug")),"title":j.get("title",""),"company":j.get("company_name",""),"location":j.get("location",""),"url":j.get("url",""),"source":provider,"description":plain_description(j.get("description","")),"remote":bool(j.get("remote",False))}
 return {}
def clean(items):
 seen=set();res=[]
 for x in items:
  url=x.get("url") or ""
  if not isinstance(url,str) or not url.startswith("https://") or url in seen: continue
  seen.add(url);res.append(x)
 return res
@app.get("/api/jobs/{provider}/{slug}")
async def board_jobs(provider:str,slug:str):
 if provider not in BOARDS or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,120}",slug): raise HTTPException(400,"Invalid board")
 url,key=BOARDS[provider]
 try:
  async with httpx.AsyncClient(timeout=15) as client:
   resp=await client.get(url.format(slug=slug));resp.raise_for_status();data=resp.json()
  entries=data if key is None else data.get(key,[])
  if not isinstance(entries,list): raise ValueError()
 except Exception: raise HTTPException(502,"Job board is unavailable or company slug not found")
 jobs=clean([normalized(provider,x,slug) for x in entries[:300] if isinstance(x,dict)])
 return {"jobs":jobs,"count":len(jobs),"source":provider}

@app.get("/api/discover")
async def discover(q:str="engineer",limit:int=80):
 q=q.strip()[:80]
 if len(q)<2: raise HTTPException(400,"Search term is too short")
 limit=max(1,min(limit,150))
 async def remotive(client):
  try:
   r=await client.get("https://remotive.com/api/remote-jobs",params={"search":q,"limit":limit},timeout=14);r.raise_for_status()
   return [normalized("remotive",j) for j in r.json().get("jobs",[])]
  except Exception:return []
 async def arbeitnow(client):
  try:
   r=await client.get("https://www.arbeitnow.com/api/job-board-api",timeout=14);r.raise_for_status()
   data=r.json().get("data",[])
   terms=q.lower().split()
   return [normalized("arbeitnow",j) for j in data if any(t in (str(j.get("title",""))+" "+str(j.get("description",""))[:150]).lower() for t in terms)]
  except Exception:return []
 async with httpx.AsyncClient() as client:
  a,b=await asyncio.gather(remotive(client),arbeitnow(client))
 jobs=clean(a+b)[:limit]
 return {"jobs":jobs,"count":len(jobs),"sources":{"remotive":len(a),"arbeitnow":len(b)},"note":"Public job feeds are not comprehensive. Some sources may temporarily be unavailable."}

from pydantic import BaseModel, Field
from typing import List, Optional

class MatchingInput(BaseModel):
 skills: List[str] = Field(default_factory=list,max_length=100)
 preferred_roles: List[str] = Field(default_factory=list,max_length=20)
 job_title: str = Field(min_length=2,max_length=250)
 job_description: str = Field(default="",max_length=20000)

@app.post("/api/match/score")
def score_match(data:MatchingInput):
 """Explainable heuristic, not a probability of getting hired."""
 title=data.job_title.lower()
 description=data.job_description.lower()
 overlap=[s.strip() for s in data.skills if s.strip() and s.strip().lower() in (title+" "+description)]
 role_hits=[role.strip() for role in data.preferred_roles if role.strip() and
            (role.strip().lower() in title or
             len(set(role.lower().split()) & set(title.split())) >= 2)]
 score=min(100,round((min(len(overlap),8)/8)*65+(35 if role_hits else 0)))
 return {"score":score,"matched_skills":overlap[:20],"matched_roles":role_hits[:10],
         "method":"keyword_overlap","disclaimer":"Relevance heuristic only; not an application or hiring guarantee."}

@app.get("/api/plans")
def plans():
 return {"billing_enabled":False,"currency":"INR","plans":[
 {"id":"free","name":"Free","price":0,"available":True},
 {"id":"pro","name":"Pro","price":None,"available":False},
 {"id":"team","name":"Teams","price":None,"available":False}],
 "notice":"Live checkout is disabled until an authorized payment provider and webhook verification are configured."}


@app.get("/api/integrations/supabase")
def supabase_integration_status():
 import os
 endpoint=os.getenv("SUPABASE_URL","")
 return {"configured":bool(endpoint and os.getenv("SUPABASE_PUBLISHABLE_KEY")),
         "project":"jobpilot-ai-production" if "sorwxnhjfwnbjuyxsota.supabase.co" in endpoint else None,
         "auth_live":False,
         "note":"Supabase client configuration present; provider sign-in and persistence must be verified independently."}

@app.get("/api/public-config")
def public_config():
 import os
 return {"url":os.getenv("SUPABASE_URL",""),"publishable_key":os.getenv("SUPABASE_PUBLISHABLE_KEY","")}

@app.middleware("http")
async def security_response_headers(request, call_next):
 response=await call_next(request)
 response.headers["X-Content-Type-Options"]="nosniff"
 response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
 response.headers["X-Frame-Options"]="DENY"
 return response

class ApplicationPacketInput(BaseModel):
 full_name: str = Field(default="",max_length=180)
 email: str = Field(default="",max_length=254)
 phone: str = Field(default="",max_length=50)
 location: str = Field(default="",max_length=180)
 years_experience: str = Field(default="",max_length=20)
 preferred_roles: str = Field(default="",max_length=400)
 company: str = Field(min_length=1,max_length=180)
 job_title: str = Field(min_length=1,max_length=250)
 apply_url: str = Field(min_length=8,max_length=2000)

def ats_provider_for_url(url:str)->str:
 from urllib.parse import urlsplit
 import ipaddress
 parsed=urlsplit(url)
 host=(parsed.hostname or "").lower().rstrip(".")
 if parsed.scheme!="https" or not host or parsed.username or parsed.password:
  raise HTTPException(422,"Valid HTTPS application URL required")
 try:
  ipaddress.ip_address(host)
  raise HTTPException(422,"IP-address application URLs are not supported")
 except ValueError:
  pass
 if host in ("localhost",) or host.endswith((".local",".internal")):
  raise HTTPException(422,"Private hostnames are not supported")
 suffixes={"greenhouse":("boards.greenhouse.io","job-boards.greenhouse.io"),"lever":("jobs.lever.co",),"ashby":("jobs.ashbyhq.com",),"smartrecruiters":("jobs.smartrecruiters.com",)}
 for provider,domains in suffixes.items():
  if host in domains:return provider
 return "external"

@app.post("/api/application/packet")
def application_packet(data:ApplicationPacketInput):
 from urllib.parse import urlsplit
 provider=ats_provider_for_url(data.apply_url)
 fields={"full_name":data.full_name.strip(),"email":data.email.strip(),"phone":data.phone.strip(),"location":data.location.strip(),"years_experience":data.years_experience.strip()}
 missing=[key for key,value in fields.items() if not value]
 return {"role":data.job_title,"company":data.company,"apply_url":data.apply_url,"ats_provider":provider,
         "candidate_fields":fields,"missing_fields":missing,
         "suggested_intro":("I am interested in the "+data.job_title+" opportunity at "+data.company+"."
            +" My preferred roles include "+data.preferred_roles.strip()+"." if data.preferred_roles.strip() else
              "I am interested in the "+data.job_title+" opportunity at "+data.company+"."),
         "required_review":["Verify eligibility and location requirements","Check salary, notice period and employer-specific questions","Attach your current resume","Review any declarations and consent before submission"],
         "submission_status":"NOT_SUBMITTED",
         "ats_readiness":{"provider":provider,"verified_form_schema":False,"required_items":["Current resume attachment","Employer-specific screening answers","Consent and declarations"],"submission_supported":False,"next_action":"Open official employer site and complete application manually"},
         "note":"Draft uses only provided facts. No application was submitted, and employer form requirements were not inspected."}


class ResumeMatchInput(BaseModel):
 resume_text: str = Field(min_length=40,max_length=30000)
 job_title: str = Field(min_length=2,max_length=250)
 job_description: str = Field(default="",max_length=20000)

@app.post("/api/resume/match")
def resume_match(data: ResumeMatchInput):
 from resume_intelligence import match_resume_to_job
 return match_resume_to_job(data.resume_text,data.job_title,data.job_description)


@app.post("/api/resume/match-file")
async def resume_match_file(file:UploadFile=File(...),job_title:str=Form(...),job_description:str=Form("")):
 from resume_intelligence import match_resume_to_job
 if not 2<=len(job_title)<=250 or len(job_description)>20000:
  raise HTTPException(422,"Invalid job requirements")
 content=await parse_resume_text(file)
 return match_resume_to_job(content,job_title,job_description)

class RecommendJob(BaseModel):
 title: str = Field(min_length=1,max_length=250)
 company: str = Field(default="",max_length=180)
 url: str = Field(default="",max_length=2000)
 description: str = Field(default="",max_length=10000)
 location: str = Field(default="",max_length=180)
 remote: bool = False
 min_experience: Optional[int] = Field(default=None,ge=0,le=50)

class RecommendInput(BaseModel):
 resume_text: str = Field(min_length=40,max_length=30000)
 jobs: List[RecommendJob] = Field(min_length=1,max_length=100)
 preferred_location: str = Field(default="",max_length=180)
 remote_only: bool = False
 max_experience: Optional[int] = Field(default=None,ge=0,le=50)

@app.post("/api/resume/recommend")
def recommend_jobs(data:RecommendInput):
 from resume_intelligence import rank_jobs
 return {"jobs":rank_jobs(data.resume_text,[j.model_dump() for j in data.jobs],data.preferred_location,data.remote_only,data.max_experience),
         "method":"skill_keyword_overlap","note":"Relevance is not hiring probability. Feed jobs may have incomplete descriptions."}
