"""Offline, fail-closed release staging preflight; never deploys or migrates."""
import re

_PROJECT_REF = re.compile(r"^[a-z0-9]{4,32}$")


def _project_ref(value):
    if not isinstance(value, str):
        return ""
    return value if _PROJECT_REF.fullmatch(value) else ""


def evaluate(settings):
    staging = _project_ref(settings.get("STAGING_PROJECT_REF"))
    production = _project_ref(settings.get("PRODUCTION_PROJECT_REF"))
    separated = bool(staging and production and staging != production)
    stage_mode = settings.get("RELEASE_TARGET") == "staging"
    locked = settings.get("PRODUCTION_APPROVED") != "yes"
    return {
        "refs_present": bool(staging and production),
        "valid_target": settings.get("RELEASE_TARGET") in ("staging", "production"),
        "separate_staging": separated,
        "staging_mode": stage_mode,
        "production_locked": locked,
        "safe_for_staging": separated and stage_mode and locked,
    }


def release_decision(settings):
    base = evaluate(settings)
    checks = {
        "staging_auth_e2e": settings.get("STAGING_AUTH_E2E_VERIFIED") == "yes",
        "staging_rls_e2e": settings.get("STAGING_RLS_E2E_VERIFIED") == "yes",
        "staging_migrations": settings.get("STAGING_MIGRATIONS_VERIFIED") == "yes",
        "release_reviewed": settings.get("RELEASE_REVIEW_APPROVED") == "yes",
    }
    return {
        "checks": checks,
        "ready_for_release_review": bool(base["safe_for_staging"] and all(checks.values())),
    }
