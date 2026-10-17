"""Opt-in discovery worker; caller supplies fetcher and state file.

Only explicit execution invokes network-capable fetcher; no email or deployment side effects.
"""
import asyncio
import random
from discovery_state import read_state, update_search, atomic_write

async def fetch_with_retry(fetcher, query, attempts=3, delay=0.25, sleep=asyncio.sleep):
    if not 1 <= attempts <= 5:
        raise ValueError("attempts must be between 1 and 5")
    for n in range(attempts):
        try:
            jobs = await fetcher(query)
            if not isinstance(jobs, list):
                raise ValueError("job feed must return a list")
            return jobs
        except (TimeoutError, ConnectionError, OSError):
            if n + 1 == attempts:
                raise
            await sleep(delay * 2**n)
    raise RuntimeError("unreachable")

async def run_once(path, search_id, query, fetcher):
    # Fetch before state mutation: errors do not mark unseen jobs as seen.
    jobs = await fetch_with_retry(fetcher, query)
    old = read_state(path)
    updated, fresh = update_search(old, search_id, query, jobs)
    atomic_write(path, updated)
    return {"search_id": search_id, "scanned": len(jobs),
            "new_jobs": fresh, "count": len(fresh),
            "notifications_sent": False}
