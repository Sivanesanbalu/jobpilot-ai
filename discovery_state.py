"""Durable, file-backed saved searches and idempotent job discovery state.

Worker foundation only: no scheduler, email, or external job fetch is started.
"""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from job_discovery_watch import new_job_matches, canonical_url

MAX_SEEN = 2000

def read_state(path):
    file = Path(path)
    if not file.exists():
        return {"searches": {}}
    data = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("searches"), dict):
        raise ValueError("Invalid discovery state")
    return data

def atomic_write(path, state):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as stream:
        tmp = Path(stream.name)
        json.dump(state, stream, ensure_ascii=False, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, target)

def update_search(state, search_id, search_query, jobs):
    """Return updated state and unseen job previews; caller persists state."""
    if not isinstance(search_id, str) or not search_id.strip() or len(search_id)>100:
        raise ValueError("Invalid search ID")
    if not isinstance(search_query, str) or not 2<=len(search_query.strip())<=80:
        raise ValueError("Invalid search query")
    if not isinstance(jobs, list) or len(jobs)>300:
        raise ValueError("Invalid jobs")
    existing=state.get("searches", {}).get(search_id, {})
    seen=list(existing.get("seen_urls", []))
    fresh=new_job_matches(seen,jobs)
    new_keys=[canonical_url(j.get("url")) for j in fresh]
    next_state={"searches":dict(state.get("searches", {}))}
    next_state["searches"][search_id]={
        "query":search_query.strip(),
        "seen_urls":(seen+new_keys)[-MAX_SEEN:],
    }
    return next_state, fresh
