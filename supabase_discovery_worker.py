"""Trusted-worker integration using an injected transactional repository.

No credentials, network connection or scheduler are started by importing this module.
The repository implementation must atomically implement lease and completion operations.
"""
from uuid import uuid4
from job_discovery_watch import canonical_url
from discovery_worker import fetch_with_retry

async def process_search(repository, fetcher, search_id, lease_seconds=300):
    """Acquire lease, record run, fetch jobs, persist notifications, release lease.

    Repository interface: acquire_lease(id,token,seconds), get_search(id),
    start_run(search), complete_run(run_id,jobs,token), fail_run(run_id,error),
    release_lease(id,token). complete_run MUST atomically insert notifications
    with a unique constraint and finalize the run to avoid partial commits.
    """
    token=str(uuid4())
    if not await repository.acquire_lease(search_id,token,lease_seconds):
        return {"status":"busy","new_jobs":0}
    run_id=None
    try:
        search=await repository.get_search(search_id)
        if not search or not search.get("is_enabled",False):
            return {"status":"disabled","new_jobs":0}
        run_id=await repository.start_run(search)
        jobs=await fetch_with_retry(fetcher,search["query"])
        distinct={}
        for job in jobs:
            url=canonical_url(job.get("url"))
            if url and url not in distinct:
                distinct[url]={"job_url":url,"title":str(job.get("title",""))[:250],
                               "company":str(job.get("company",""))[:180]}
        inserted=await repository.complete_run(run_id,list(distinct.values()),token)
        return {"status":"succeeded","new_jobs":inserted,"scanned":len(jobs)}
    except Exception as error:
        if run_id is not None:
            try:
                await repository.fail_run(run_id,str(error)[:500])
            except Exception as recording_error:
                error.add_note("Failed to record discovery run failure: " + type(recording_error).__name__)
        raise
    finally:
        try:
            await repository.release_lease(search_id,token)
        except Exception:
            # A TTL-backed lease expires even if release fails. Do not suppress
            # a database error here: the caller must know cleanup was incomplete.
            raise
