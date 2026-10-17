"""Fail-closed staging release environment checks. No external connections."""

import re

_REF = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")

def _ref(value):
    if not isinstance(value, str):
        return ""
    value = value.strip()
    return value if _REF.fullmatch(value) else ""

def evaluate(settings):
    staging = _ref(settings.get("STAGING_PROJECT_REF"))
    production = _ref(settings.get("PRODUCTION_PROJECT_REF"))
    target = str(settings.get("RELEASE_TARGET") or "").strip()
    approved = str(settings.get("PRODUCTION_APPROVED") or "").strip().lower()
    refs_present = bool(staging and production)
    separate = bool(refs_present and staging.casefold() != production.casefold())
    staging_mode = target == "staging"
    production_locked = approved != "yes"
    return {
        "separate_staging": separate,
        "staging_mode": staging_mode,
        "production_locked": production_locked,
        "valid_target": target in {"staging", "production"},
        "refs_present": refs_present,
        "safe_for_staging": bool(separate and staging_mode and production_locked),
    }

def release_decision(settings):
    status = evaluate(settings)
    checks = {
        "environment": status["safe_for_staging"],
        "staging_auth_e2e": settings.get("STAGING_AUTH_E2E_VERIFIED") == "yes",
        "staging_rls_e2e": settings.get("STAGING_RLS_E2E_VERIFIED") == "yes",
        "staging_migrations": settings.get("STAGING_MIGRATIONS_VERIFIED") == "yes",
        "release_reviewed": settings.get("RELEASE_REVIEW_APPROVED") == "yes",
    }
    return {"ready_for_release_review": all(checks.values()), "checks": checks}
