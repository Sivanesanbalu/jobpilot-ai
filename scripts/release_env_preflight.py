"""Fail-closed, offline checks for staging release targets and evidence."""

import re

PROJECT_REF = re.compile(r"^[a-z0-9]{8,32}$")
EVIDENCE = {
    "staging_auth_e2e": "STAGING_AUTH_E2E_VERIFIED",
    "staging_rls_e2e": "STAGING_RLS_E2E_VERIFIED",
    "staging_migrations": "STAGING_MIGRATIONS_VERIFIED",
    "release_reviewed": "RELEASE_REVIEW_APPROVED",
}


def _valid_ref(value):
    return isinstance(value, str) and bool(PROJECT_REF.fullmatch(value))


def evaluate(settings):
    staging = settings.get("STAGING_PROJECT_REF")
    production = settings.get("PRODUCTION_PROJECT_REF")
    valid_refs = _valid_ref(staging) and _valid_ref(production)
    separate = bool(valid_refs and staging != production)
    mode = settings.get("RELEASE_TARGET") == "staging"
    locked = settings.get("PRODUCTION_APPROVED") != "yes"
    return {
        "refs_present": bool(staging and production and isinstance(staging, str) and isinstance(production, str) and staging.strip() and production.strip()),
        "valid_project_refs": valid_refs,
        "separate_staging": separate,
        "valid_target": settings.get("RELEASE_TARGET") in ("staging", "production"),
        "staging_mode": mode,
        "production_locked": locked,
        "safe_for_staging": bool(separate and mode and locked),
    }


def release_decision(settings):
    """Return evidence status; this is a review aid, never deployment approval."""
    checks = {key: settings.get(variable) == "yes" for key, variable in EVIDENCE.items()}
    staging = settings.get("STAGING_PROJECT_REF")
    production = settings.get("PRODUCTION_PROJECT_REF")
    # The release-review decision is only meaningful with distinct, non-empty
    # references. Full project-ref syntax belongs to evaluate() for deployment.
    distinct = bool(isinstance(staging, str) and isinstance(production, str) and staging.strip() and production.strip() and staging != production)
    return {"checks": checks, "ready_for_release_review": bool(distinct and settings.get("RELEASE_TARGET") == "staging" and all(checks.values()))}
