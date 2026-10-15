from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pathlib import Path
from io import BytesIO
import asyncio, re, httpx
from pypdf import PdfReader

app=FastAPI(title="JobPilot AI",version="0.4.0")
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
 return "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>JobPilot AI — Career copilot</title><style>\n:root{font-family:Inter,system-ui,sans-serif;color:#eaf0ff;background:#080d19}*{box-sizing:border-box}body{margin:0}a{color:#a8b7ff}button,input,select{font:inherit;border-radius:10px;padding:11px 14px}button{background:#775dff;color:white;border:0;cursor:pointer}button.secondary{background:#253049}button:hover{filter:brightness(1.16)}input,select{background:#10182a;color:white;border:1px solid #3e4b64}header{position:sticky;top:0;z-index:2;backdrop-filter:blur(12px);background:#080d19e8;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #27334a;padding:16px max(24px,calc((100vw - 1140px)/2))}.logo{font-size:20px;font-weight:800;letter-spacing:-.5px}nav{display:flex;gap:16px;align-items:center}nav button{background:transparent;padding:6px 8px;color:#acbad7}.wrap{max-width:1140px;padding:34px 20px;margin:auto}.hero{text-align:center;padding:82px 16px 66px;background:radial-gradient(ellipse at 50% 0%,#39277180,transparent 60%)}.hero h1{font-size:clamp(38px,6vw,65px);letter-spacing:-2px;line-height:1.05;margin:15px auto;max-width:800px}.sub{color:#9eacc9;line-height:1.7}.hero .sub{max-width:650px;margin:20px auto 28px}.eyebrow{color:#a89aff;letter-spacing:2px;text-transform:uppercase;font-size:12px;font-weight:800}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.card{background:#121a2b;border:1px solid #2c3952;border-radius:18px;padding:24px}.card h3{margin-top:8px}.kpi{font-size:33px;font-weight:800}.layout{display:grid;grid-template-columns:240px 1fr;gap:22px}.sidebar button{display:block;text-align:left;width:100%;margin:8px 0;background:transparent}.sidebar button.active{background:#303151}.toolbar{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px}.toolbar input{flex:1;min-width:160px}.job{padding:17px 0;border-top:1px solid #2b3750;display:flex;gap:12px;align-items:center;justify-content:space-between}.job .meta{color:#9caac5;font-size:13px;margin:6px 0}.tag{display:inline-block;padding:5px 9px;border:1px solid #53617a;border-radius:20px;font-size:12px;margin:4px 4px 4px 0;color:#d4d9f5}.muted{color:#92a1c0}section{margin:30px 0 60px}.hide{display:none!important}.price{font-size:32px;font-weight:bold}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.form-grid label{display:grid;gap:7px;color:#a9b8d7}.form-grid input{width:100%}footer{text-align:center;padding:35px;border-top:1px solid #27344b;color:#8291af}#notice{margin-top:12px;color:#d7ccff}@media(max-width:760px){nav{gap:3px}nav button{font-size:12px}.grid{grid-template-columns:1fr}.layout{grid-template-columns:1fr}.sidebar{display:flex;gap:5px;overflow:auto}.sidebar button{min-width:max-content}.form-grid{grid-template-columns:1fr}.job{align-items:flex-start;flex-direction:column}.hero{padding:55px 14px}}</style></head><body>\n<header><div class=\"logo\">✦ JobPilot <span style=\"color:#a293ff\">AI</span></div><nav><button onclick=\"show('landing')\">Home</button><button onclick=\"show('pricing')\">Pricing</button><button onclick=\"show('dashboard')\">Dashboard</button></nav></header>\n<div id=\"landing\"><div class=\"hero\"><div class=\"eyebrow\">Your career. One intelligent workspace.</div><h1>Find jobs that fit.<br>Apply with confidence.</h1><p class=\"sub\">Upload your resume, discover roles across public hiring feeds and company career boards, and organize every application in one place.</p><button onclick=\"show('onboarding')\">Get started free →</button> <button class=\"secondary\" onclick=\"show('dashboard')\">Explore job finder</button><p class=\"muted\" style=\"font-size:13px;margin-top:20px\">No automatic applications are sent without your review.</p></div><div class=\"wrap\"><div class=\"grid\"><div class=\"card\"><div style=\"font-size:26px\">📄</div><h3>Resume intelligence</h3><p class=\"sub\">Extract skills and suggest career paths from your PDF or text resume.</p></div><div class=\"card\"><div style=\"font-size:26px\">🌍</div><h3>Broader job discovery</h3><p class=\"sub\">Explore Remotive and Arbeitnow feeds, plus Greenhouse, Lever, Ashby and SmartRecruiters boards.</p></div><div class=\"card\"><div style=\"font-size:26px\">✅</div><h3>Application workspace</h3><p class=\"sub\">Review employer applications and track saved and applied positions privately in your browser.</p></div></div></div></div>\n<div class=\"wrap hide\" id=\"onboarding\"><div class=\"eyebrow\">Setup / 01</div><h1>Build your career profile</h1><p class=\"sub\">Your profile is saved in this browser only. This version doesn't have user accounts or cloud sync yet.</p><div class=\"card\"><form id=\"profile\"><div class=\"form-grid\"><label>Full name<input id=\"fullName\" required placeholder=\"Full name\"></label><label>Email<input id=\"email\" type=\"email\" required placeholder=\"you@example.com\"></label><label>Phone<input id=\"phone\" placeholder=\"+91 ...\"></label><label>Location<input id=\"location\" placeholder=\"City / Remote\"></label><label>Experience (years)<input id=\"experience\" type=\"number\" min=\"0\" max=\"50\" step=\".5\"></label><label>Preferred roles<input id=\"roleInput\" placeholder=\"AI Engineer, Frontend Developer\"></label></div><p class=\"muted\">Resume upload (PDF/TXT up to 4 MB)</p><input id=\"resume\" type=\"file\" accept=\".pdf,.txt\"><p id=\"resumeNote\" class=\"sub\"></p><button type=\"submit\">Analyze & save profile →</button></form></div></div>\n<div class=\"wrap hide\" id=\"dashboard\"><div class=\"layout\"><aside class=\"sidebar card\"><button class=\"active\" onclick=\"tab('overview',this)\">◉ Overview</button><button onclick=\"tab('jobs',this)\">⌕ Discover jobs</button><button onclick=\"tab('applications',this)\">▤ My applications</button><button onclick=\"show('onboarding')\">♙ Edit profile</button><button onclick=\"show('pricing')\">◇ Plans</button></aside><main><div id=\"overview\"><div class=\"eyebrow\">Workspace</div><h1>Welcome <span id=\"welcome\">back</span> 👋</h1><p class=\"sub\">Find suitable opportunities and keep your job search organized.</p><div class=\"grid\"><div class=\"card\"><div class=\"kpi\" id=\"savedCount\">0</div><p class=\"muted\">Tracked jobs</p></div><div class=\"card\"><div class=\"kpi\" id=\"appliedCount\">0</div><p class=\"muted\">Marked applied</p></div><div class=\"card\"><div class=\"kpi\" id=\"roleCount\">0</div><p class=\"muted\">Suggested roles</p></div></div><section class=\"card\"><h2>Resume-based suggestions</h2><div id=\"suggestions\" class=\"sub\">Upload a resume in your profile to get career suggestions.</div><p><button onclick=\"tab('jobs')\">Find matching jobs →</button></p></section></div>\n<div class=\"hide\" id=\"jobs\"><h1>Discover jobs</h1><p class=\"sub\">Search public listings. Add a company board for roles not found in general feeds.</p><div class=\"card\"><h3>Search job feeds</h3><div class=\"toolbar\"><input id=\"search\" value=\"AI engineer\" placeholder=\"Job title or keyword\"><button onclick=\"discover()\">Search jobs</button><button class=\"secondary\" onclick=\"searchFromResume()\">Use my suggested role</button></div><h3>Search a company ATS</h3><div class=\"toolbar\"><select id=\"provider\"><option value=\"greenhouse\">Greenhouse</option><option value=\"lever\">Lever</option><option value=\"ashby\">Ashby</option><option value=\"smartrecruiters\">SmartRecruiters</option></select><input id=\"slug\" placeholder=\"Company board identifier\"><button class=\"secondary\" onclick=\"board()\">Fetch board</button></div><small class=\"muted\">Not every job website allows public indexing or automated application. Data can be incomplete or delayed.</small></div><div class=\"card\"><h2>Open positions</h2><div id=\"jobResults\" class=\"sub\">Search to view available jobs.</div></div></div>\n<div class=\"hide\" id=\"applications\"><h1>Application tracker</h1><p class=\"sub\">Local tracking only. Clicking Apply opens the employer's official page; mark as applied once you submit.</p><div class=\"card\" id=\"tracked\">No tracked jobs yet.</div></div></main></div></div>\n<div class=\"wrap hide\" id=\"pricing\"><div class=\"eyebrow\">Simple pricing</div><h1>Choose your JobPilot plan</h1><p class=\"sub\">Plan previews only — billing checkout isn't enabled yet, and no payment will be collected.</p><div class=\"grid\"><div class=\"card\"><h2>Free</h2><div class=\"price\">₹0</div><p class=\"sub\">Explore public job discovery and local application tracking.</p><button onclick=\"show('onboarding')\">Start free</button></div><div class=\"card\"><h2>Pro — planned</h2><div class=\"price\">Coming soon</div><p class=\"sub\">Cloud profiles, saved searches, recommendations and workflow automation.</p><button class=\"secondary\" disabled>Not available</button></div><div class=\"card\"><h2>Teams — planned</h2><div class=\"price\">Contact us</div><p class=\"sub\">Team-level reporting and organization management are on the roadmap.</p><button class=\"secondary\" disabled>Not available</button></div></div></div>\n<section class=\"wrap\" id=\"accountPanel\"><div class=\"card\"><h2>🔐 Your JobPilot account</h2><p class=\"sub\">Create an account to sync your profile and applications securely across devices. Email verification may be required.</p><div id=\"accountLoggedOut\"><div class=\"toolbar\"><input id=\"authEmail\" type=\"email\" placeholder=\"Email address\" autocomplete=\"email\"><input id=\"authPassword\" type=\"password\" placeholder=\"Password (at least 8 characters)\" autocomplete=\"current-password\"></div><div class=\"toolbar\"><button id=\"signUpBtn\">Create account</button><button class=\"secondary\" id=\"signInBtn\">Sign in</button><button class=\"secondary\" id=\"forgotPasswordBtn\">Reset password</button></div></div><div id=\"accountLoggedIn\" class=\"hide\"><p id=\"accountUser\"></p><div class=\"toolbar\"><button id=\"syncProfileBtn\">Sync profile to cloud</button><button id=\"syncApplicationsBtn\">Sync saved applications</button><button class=\"secondary\" id=\"cloudLoadBtn\">Load my cloud data</button><button class=\"secondary\" id=\"signOutBtn\">Sign out</button><button class=\"secondary\" id=\"changePasswordBtn\">Change password</button></div></div><p id=\"authMessage\" class=\"sub\" role=\"status\"></p></div></section><footer>JobPilot AI © 2026 · Public job discovery · No guaranteed placement · Apply through official employer sites</footer>\n<script>\nconst sections=['landing','onboarding','dashboard','pricing'];const $=id=>document.getElementById(id);const get=(key,def)=>{try{return JSON.parse(localStorage.getItem('jp_'+key))??def}catch{return def}};const put=(key,val)=>{localStorage.setItem('jp_'+key,JSON.stringify(val));window.dispatchEvent(new CustomEvent('jobpilot-local-change',{detail:{key}}))};let profile=get('profile',{}),tracked=get('tracked',[]),roles=get('roles',[]),results=[];\nfunction show(which){for(const s of sections)$(s).classList.toggle('hide',s!==which);window.scrollTo(0,0);refresh()}\nfunction tab(t,b){show('dashboard');for(const id of ['overview','jobs','applications'])$(id).classList.toggle('hide',t!==id);document.querySelectorAll('.sidebar button').forEach(x=>x.classList.remove('active'));if(b)b.classList.add('active');if(t==='applications')renderTracked()}\nfunction esc(s){return String(s??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]))}\nfunction refresh(){$('welcome').textContent=profile.name?.split(' ')[0]||'back';$('savedCount').textContent=tracked.length;$('appliedCount').textContent=tracked.filter(x=>x.status==='Applied').length;$('roleCount').textContent=roles.length;$('suggestions').textContent=roles.length?roles.map(x=>x.role+(x.skills?.length?' ('+x.skills.slice(0,3).join(', ')+')':'')).join(' · '):'Upload your resume to discover suggested roles.';for(const [key,id] of [['name','fullName'],['email','email'],['phone','phone'],['location','location'],['experience','experience'],['roles','roleInput']]) if(profile[key]!==undefined)$(id).value=profile[key]}\n$('profile').addEventListener('submit',async e=>{e.preventDefault();let p={name:$('fullName').value,email:$('email').value,phone:$('phone').value,location:$('location').value,experience:$('experience').value,roles:$('roleInput').value};const f=$('resume').files[0],notice=$('resumeNote');notice.textContent='Saving profile…';if(f){try{notice.textContent='Analyzing resume…';let fd=new FormData();fd.append('file',f);let r=await fetch('/api/resume/analyze',{method:'POST',body:fd});let data=await r.json();if(!r.ok)throw Error(data.detail||'Analysis failed');roles=data.suggested_roles;put('roles',roles);if(!p.roles)p.roles=roles.map(x=>x.role).join(', ');notice.textContent='Resume analyzed. Original file is not saved.'}catch(err){notice.textContent='Could not analyze resume: '+err.message;return}}profile=p;put('profile',profile);refresh();tab('overview')});\nasync function discover(){let q=$('search').value.trim();if(!q)return;$('jobResults').textContent='Searching public feeds…';try{let r=await fetch('/api/discover?q='+encodeURIComponent(q));let d=await r.json();if(!r.ok)throw Error(d.detail);results=d.jobs;renderJobs()}catch(err){$('jobResults').textContent='Search unavailable: '+err.message}}\nasync function board(){let slug=$('slug').value.trim(),provider=$('provider').value;if(!slug)return;$('jobResults').textContent='Fetching company board…';try{let r=await fetch('/api/jobs/'+encodeURIComponent(provider)+'/'+encodeURIComponent(slug));let d=await r.json();if(!r.ok)throw Error(d.detail);results=d.jobs;renderJobs()}catch(err){$('jobResults').textContent='Board fetch error: '+err.message}}\nfunction searchFromResume(){const role=roles?.[0]?.role||profile.roles?.split(\",\")[0];if(!role){alert(\"Add a resume or preferred roles in Profile first.\");return}document.getElementById(\"search\").value=role;discover()}\nfunction renderJobs(){let root=$('jobResults');root.replaceChildren();let p=document.createElement('p');p.className='muted';p.textContent=results.length+' listings returned';root.append(p);for(let i=0;i<results.length;i++){let x=results[i],d=document.createElement('div');d.className='job';let left=document.createElement('div');left.innerHTML='<strong>'+esc(x.title)+'</strong><div class=\"meta\">'+esc(x.company||'Employer')+' · '+esc(x.location||'Location not specified')+' · '+esc(x.source)+'</div>';let right=document.createElement('div');let a=document.createElement('a');a.href=x.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Official apply ↗';let b=document.createElement('button');b.className='secondary';b.style.marginLeft='10px';b.textContent=tracked.some(t=>t.url===x.url)?'Saved ✓':'Save';b.onclick=()=>{if(!tracked.some(t=>t.url===x.url)){tracked.unshift({...x,status:'Saved'});put('tracked',tracked);b.textContent='Saved ✓';refresh()}};right.append(a,b);d.append(left,right);root.append(d)}if(!results.length)root.append(document.createTextNode('No matching jobs found from available feeds. Try broader keywords or a company board.'))}\nfunction renderTracked(){let root=$('tracked');root.replaceChildren();if(!tracked.length){root.textContent='No jobs tracked yet. Save jobs from Discover jobs.';return}for(let i=0;i<tracked.length;i++){let j=tracked[i],d=document.createElement('div');d.className='job';let label=document.createElement('div');label.innerHTML='<strong>'+esc(j.title)+'</strong><div class=\"meta\">'+esc(j.company)+' · '+esc(j.status)+'</div>';let actions=document.createElement('div'),a=document.createElement('a');a.href=j.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Apply ↗';let select=document.createElement('select');for(let st of ['Saved','Applied','Interview','Offer','Rejected']){let opt=document.createElement('option');opt.textContent=st;select.append(opt)}select.value=j.status;select.onchange=()=>{j.status=select.value;put('tracked',tracked);refresh();renderTracked()};let remove=document.createElement('button');remove.className='secondary';remove.textContent='Remove';remove.onclick=()=>{tracked.splice(i,1);put('tracked',tracked);refresh();renderTracked()};actions.append(a,select,remove);d.append(label,actions);root.append(d)}}\nwindow.addEventListener('jobpilot-cloud-loaded',()=>{profile=get('profile',{});tracked=get('tracked',[]);roles=get('roles',[]);refresh();if(!document.getElementById('applications').classList.contains('hide'))renderTracked();});\nrefresh();\n</script><script type=\"module\">\nimport {createClient} from \"https://esm.sh/@supabase/supabase-js@2.57.4\";\nlet sb=null,user=null,syncReady=false,syncTimer=0,loading=false;\nconst $=id=>document.getElementById(id);\nconst notice=t=>{$(\"authMessage\").textContent=t};\nconst profile=()=>JSON.parse(localStorage.getItem(\"jp_profile\")||\"{}\");\nconst jobs=()=>JSON.parse(localStorage.getItem(\"jp_tracked\")||\"[]\");\nconst setLocal=(k,v)=>localStorage.setItem(\"jp_\"+k,JSON.stringify(v));\nconst statusToDb={Saved:\"saved\",Applied:\"submitted\",Interview:\"interview\",Offer:\"offer\",Rejected:\"rejected\"};\nconst statusFromDb={saved:\"Saved\",submitted:\"Applied\",interview:\"Interview\",offer:\"Offer\",rejected:\"Rejected\",ready_for_review:\"Saved\"};\nasync function cloudLoad(){\n if(!user||loading)return;\n loading=true;\n try {\n  const [p,a]=await Promise.all([\n   sb.from(\"profiles\").select(\"*\").eq(\"user_id\",user.id).maybeSingle(),\n   sb.from(\"applications\").select(\"*\").eq(\"user_id\",user.id).order(\"created_at\",{ascending:false})]);\n  if(p.error||a.error)throw(p.error||a.error);\n  if(p.data)setLocal(\"profile\",{...profile(),name:p.data.full_name||\"\",location:p.data.location||\"\",roles:(p.data.preferred_roles||[]).join(\", \"),experience:p.data.years_experience});\n  setLocal(\"tracked\",a.data.map(x=>({company:x.company,title:x.title,url:x.apply_url,status:statusFromDb[x.status]||\"Saved\"})));\n  window.dispatchEvent(new Event(\"jobpilot-cloud-loaded\"));\n  notice(\"Cloud data loaded. Auto-sync is ready after you enable it below.\");\n }catch(e){notice(\"Cloud load failed: \"+e.message)}\n finally{loading=false}\n}\nfunction display(){\n $(\"accountLoggedOut\").classList.toggle(\"hide\",!!user);\n $(\"accountLoggedIn\").classList.toggle(\"hide\",!user);\n $(\"accountUser\").textContent=user?\"Signed in as \"+user.email:\"\";\n}\nasync function saveProfile(){\n if(!user)return;\n const p=profile();\n const {error}=await sb.from(\"profiles\").upsert({user_id:user.id,full_name:p.name||\"\",location:p.location||\"\",preferred_roles:(p.roles||\"\").split(\",\").map(s=>s.trim()).filter(Boolean),years_experience:p.experience?Number(p.experience):null,updated_at:new Date().toISOString()},{onConflict:\"user_id\"});\n if(error)throw error;\n}\nasync function saveJobs(){\n if(!user)return;\n for(const j of jobs()){\n  if(!j.url||!j.url.startsWith(\"https://\"))continue;\n  const payload={user_id:user.id,company:j.company||\"Unknown\",title:j.title||\"Untitled\",apply_url:j.url,status:statusToDb[j.status]||\"saved\"};\n  const result=await sb.from(\"applications\").upsert(payload,{onConflict:\"user_id,apply_url\"});\n  if(result.error)throw result.error;\n }\n}\nasync function sync(kind){\n if(!user||loading)return;\n try{\n  if(kind===\"profile\")await saveProfile();\n  if(kind===\"tracked\")await saveJobs();\n  notice(\"Cloud \"+(kind===\"profile\"?\"profile\":\"applications\")+\" saved successfully.\");\n }catch(e){notice(\"Sync failed: \"+e.message)}\n}\nfunction queueSync(kind){\n if(!syncReady||!user||loading||![\"profile\",\"tracked\"].includes(kind))return;\n clearTimeout(syncTimer);\n syncTimer=setTimeout(()=>sync(kind),1200);\n}\nwindow.addEventListener(\"jobpilot-local-change\",e=>queueSync(e.detail.key));\ntry{\n const config=await fetch(\"/api/public-config\").then(r=>r.json());\n if(!config.url||!config.publishable_key)throw Error(\"Cloud accounts not configured.\");\n sb=createClient(config.url,config.publishable_key,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});\n const {data}=await sb.auth.getUser();user=data.user;display();\n if(user)await cloudLoad();\n sb.auth.onAuthStateChange((event,session)=>{\n  const changed=user?.id!==session?.user?.id;\n  user=session?.user||null;syncReady=false;clearTimeout(syncTimer);display();\n  if(event===\"SIGNED_IN\"&&changed)queueMicrotask(()=>cloudLoad());\n  if(event===\"SIGNED_OUT\"){setLocal(\"tracked\",[]);setLocal(\"profile\",{});sessionStorage.removeItem(\"jp_cloud_loaded\");location.reload()}\n });\n $(\"signUpBtn\").onclick=async()=>{\n  const email=$(\"authEmail\").value.trim(),password=$(\"authPassword\").value;\n  if(password.length<8){notice(\"Password must have at least eight characters.\");return}\n  const {error,data}=await sb.auth.signUp({email,password,options:{emailRedirectTo:location.origin+\"/\"}});\n  notice(error?error.message:data.session?\"Signed up and signed in.\":\"Check your email to verify your account.\");\n };\n $(\"signInBtn\").onclick=async()=>{const {error}=await sb.auth.signInWithPassword({email:$(\"authEmail\").value.trim(),password:$(\"authPassword\").value});notice(error?error.message:\"Signed in. Cloud data is being loaded.\")};\n $(\"forgotPasswordBtn\").onclick=async()=>{const email=$(\"authEmail\").value.trim();if(!email){notice(\"Enter your email address first.\");return}const {error}=await sb.auth.resetPasswordForEmail(email,{redirectTo:location.origin+\"/\"});notice(error?error.message:\"If the email belongs to an account, recovery instructions will arrive shortly.\")};\n $(\"changePasswordBtn\").onclick=async()=>{const password=prompt(\"Enter a new password (at least 8 characters)\");if(password===null)return;if(password.length<8){notice(\"Password must have at least eight characters.\");return}const {error}=await sb.auth.updateUser({password});notice(error?error.message:\"Password changed.\")};\n $(\"signOutBtn\").onclick=async()=>{const {error}=await sb.auth.signOut();if(error)notice(error.message)};\n $(\"syncProfileBtn\").onclick=async()=>{syncReady=true;await sync(\"profile\");notice(\"Profile synced. Auto-sync enabled for this session.\")};\n $(\"syncApplicationsBtn\").onclick=async()=>{syncReady=true;await sync(\"tracked\");notice(\"Applications synced. Auto-sync enabled for this session.\")};\n $(\"cloudLoadBtn\").onclick=()=>cloudLoad();\n}catch(e){notice(\"Account setup unavailable: \"+e.message)}\n</script></body></html>"
@app.get("/api/health")
def health():
 return {"ok":True,"version":"0.4.0","storage":"browser only","applications":"manual approval"}

@app.post("/api/resume/analyze")
async def analyze_resume(file:UploadFile=File(...)):
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
 lower=content.lower()
 scores=[]
 for role,words in ROLE_RULES.items():
  matched=[w for w in words if w in lower]
  scores.append({"role":role,"score":len(matched),"skills":matched})
 scores=sorted(scores,key=lambda a:-a["score"])
 found=sorted({x for r in scores for x in r["skills"]})
 return {"suggested_roles":[s for s in scores if s["score"]>0][:5] or scores[:3],"skills":found[:30],"extracted_characters":len(content),"note":"Resume parsed in memory and not stored on the server. Review recommendations before using."}

def normalized(provider,j,slug=""):
 if provider=="greenhouse": return {"id":str(j.get("id")),"title":j.get("title",""),"company":slug,"location":(j.get("location") or {}).get("name",""),"url":j.get("absolute_url",""),"source":provider}
 if provider=="lever": return {"id":str(j.get("id")),"title":j.get("text",""),"company":slug,"location":(j.get("categories") or {}).get("location",""),"url":j.get("hostedUrl",""),"source":provider}
 if provider=="ashby": return {"id":str(j.get("id")),"title":j.get("title",""),"company":slug,"location":j.get("location",""),"url":j.get("applyUrl") or j.get("jobUrl",""),"source":provider}
 if provider=="smartrecruiters": return {"id":str(j.get("id")),"title":j.get("name",""),"company":slug,"location":(j.get("location") or {}).get("city",""),"url":j.get("ref",""),"source":provider}
 if provider=="remotive": return {"id":str(j.get("id")),"title":j.get("title",""),"company":j.get("company_name",""),"location":j.get("candidate_required_location",""),"url":j.get("url",""),"source":provider}
 if provider=="arbeitnow": return {"id":str(j.get("slug")),"title":j.get("title",""),"company":j.get("company_name",""),"location":j.get("location",""),"url":j.get("url",""),"source":provider}
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
from typing import List

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
         "note":"Supabase credentials configured; authenticated user flows are not yet enabled."}

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
