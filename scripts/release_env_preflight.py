"""Offline, fail-closed checks for release target identity and approval state."""

import re

_PROJECT_REF = re.compile(r"^[a-z0-9]{8,32}$")


def _project_ref(value):
    """Accept Supabase project refs only, not URLs, whitespace, or placeholders."""
    if not isinstance(value, str):
        return ""
    return value if _PROJECT_REF.fullmatch(value) else ""


def evaluate(settings):
    staging = _project_ref(settings.get("STAGING_PROJECT_REF", ""))
    production = _project_ref(settings.get("PRODUCTION_PROJECT_REF", ""))
    return {
        "separate_staging": bool(staging and production and staging != production),
        "staging_mode": settings.get("RELEASE_TARGET") == "staging",
        "production_locked": settings.get("PRODUCTION_APPROVED") != "yes",
    }
