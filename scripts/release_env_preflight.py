"""Evaluate release environment isolation offline. Never deploy from this module."""

def evaluate(settings):
    staging = settings.get("STAGING_PROJECT_REF", "").strip()
    production = settings.get("PRODUCTION_PROJECT_REF", "").strip()
    target = settings.get("RELEASE_TARGET", "").strip().lower()
    approval = settings.get("PRODUCTION_APPROVED", "").strip().lower()
    valid_ref = lambda ref: bool(ref) and all(c.isalnum() or c == "-" for c in ref)
    return {
        "separate_staging": valid_ref(staging) and valid_ref(production) and staging != production,
        "staging_mode": target == "staging",
        "production_locked": approval != "yes",
    }
