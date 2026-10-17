"""Validate deployment environment identity without connecting to external systems."""

def evaluate(settings):
    staging = settings.get("STAGING_PROJECT_REF", "").strip()
    production = settings.get("PRODUCTION_PROJECT_REF", "").strip()
    target = settings.get("RELEASE_TARGET", "").strip()
    approved = settings.get("PRODUCTION_APPROVED", "").strip().lower()
    return {
        "separate_staging": bool(staging and production and staging != production),
        "staging_mode": target == "staging",
        "production_locked": approved != "yes",
        "valid_target": target in {"staging", "production"},
        "refs_present": bool(staging and production),
    }
