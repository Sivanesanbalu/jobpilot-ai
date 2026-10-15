"""Pure job-change detection used by scheduled discovery workers.

No outbound messages or database writes happen in this module.
"""
from urllib.parse import urlsplit, urlunsplit

def canonical_url(url):
    if not isinstance(url, str):
        return ""
    try:
        p = urlsplit(url.strip())
        if p.scheme.lower() != "https" or not p.hostname:
            return ""
        host = p.hostname.lower()
        netloc = host + ((":" + str(p.port)) if p.port else "")
        return urlunsplit(("https", netloc, p.path.rstrip("/") or "/", p.query, ""))
    except ValueError:
        return ""

def new_job_matches(previous_urls, jobs):
    """Return unseen valid jobs once each, preserving feed order."""
    seen = {canonical_url(u) for u in previous_urls}
    result = []
    for job in jobs:
        key = canonical_url(job.get("url", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(job)
    return result
