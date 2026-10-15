"""Offline scheduler and idempotent notification outbox foundation.

Execution is explicit. No background daemon, outbound email, or real scheduler is started.
"""
from datetime import datetime, timedelta, timezone
from job_discovery_watch import canonical_url

def due_searches(searches, now=None):
    now=now or datetime.now(timezone.utc)
    due=[]
    for search in searches:
        if not search.get("enabled",True):
            continue
        interval=search.get("interval_minutes",360)
        if type(interval) is not int or not 60<=interval<=10080:
            raise ValueError("Interval must be an integer between 60 and 10080 minutes")
        last=search.get("last_run_at")
        if last is None:
            due.append(search)
            continue
        then=datetime.fromisoformat(last.replace("Z","+00:00"))
        if then.tzinfo is None:
            raise ValueError("last_run_at must include timezone")
        if now>=then+timedelta(minutes=interval):
            due.append(search)
    return due

def enqueue_notifications(outbox, user_id, search_id, jobs):
    """Return an updated outbox; stable keys prevent duplicate notifications."""
    updated=dict(outbox)
    inserted=[]
    for job in jobs:
        url=canonical_url(job.get("url"))
        if not url:
            continue
        key=f"{user_id}:{search_id}:{url}"
        if key in updated:
            continue
        record={"user_id":user_id,"search_id":search_id,"job_url":url,
                "title":str(job.get("title",""))[:250],"status":"pending","attempts":0}
        updated[key]=record
        inserted.append(record)
    return updated,inserted

def mark_delivery(outbox, key, success, max_attempts=3):
    if key not in outbox:
        raise KeyError("Unknown notification")
    if not 1<=max_attempts<=10:
        raise ValueError("Invalid retry limit")
    updated=dict(outbox)
    item=dict(updated[key])
    if item["status"] in ("delivered","failed"):
        return updated
    item["attempts"]+=1
    item["status"]="delivered" if success else ("failed" if item["attempts"]>=max_attempts else "pending")
    updated[key]=item
    return updated
