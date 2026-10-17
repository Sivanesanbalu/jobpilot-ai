"""Check release targets without connecting to external systems."""

import re

PROJECT_REF = re.compile(r"^[a-z0-9]{8,32}$")


def evaluate(settings):
    staging = str(settings.get("STAGING_PROJECT_REF") or "").strip()
    production = str(settings.get("PRODUCTION_PROJECT_REF") or "").strip()
    valid_refs = bool(PROJECT_REF.fullmatch(staging) and PROJECT_REF.fullmatch(production))
    return {
        "separate_staging": bool(staging and production and staging != production),
        "staging_mode": settings.get("RELEASE_TARGET") == "staging",
        "production_locked": settings.get("PRODUCTION_APPROVED") != "yes",
        "valid_project_refs": valid_refs,
    }
