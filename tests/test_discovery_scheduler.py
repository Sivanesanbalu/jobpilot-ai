from datetime import datetime, timezone
from discovery_scheduler import due_searches, enqueue_notifications, mark_delivery

def test_due_scheduler_respects_interval():
    now=datetime(2026,10,15,12,tzinfo=timezone.utc)
    jobs=[{"id":"ready","interval_minutes":60,"last_run_at":"2026-10-15T10:00:00+00:00"},
          {"id":"later","interval_minutes":60,"last_run_at":"2026-10-15T11:30:00+00:00"},
          {"id":"disabled","enabled":False}]
    assert [x["id"] for x in due_searches(jobs,now)]==["ready"]

def test_duplicate_jobs_only_one_notification():
    jobs=[{"url":"https://EXAMPLE.com/job/1/","title":"ML Engineer"},{"url":"https://example.com/job/1","title":"Duplicate"}]
    state,queued=enqueue_notifications({},"u1","search1",jobs)
    assert len(queued)==1
    same,again=enqueue_notifications(state,"u1","search1",jobs)
    assert same==state and again==[]

def test_bounded_notification_retries():
    initial,_=enqueue_notifications({},"u1","search1",[{"url":"https://example.com/job"}])
    key=next(iter(initial))
    first=mark_delivery(initial,key,False,max_attempts=2)
    assert first[key]["status"]=="pending"
    second=mark_delivery(first,key,False,max_attempts=2)
    assert second[key]["status"]=="failed"
    assert mark_delivery(second,key,True)==second

def test_delivery_marked_once():
    state,_=enqueue_notifications({},"u1","search1",[{"url":"https://example.com/job"}])
    key=next(iter(state))
    delivered=mark_delivery(state,key,True)
    assert delivered[key]["status"]=="delivered"
    assert mark_delivery(delivered,key,True)==delivered
