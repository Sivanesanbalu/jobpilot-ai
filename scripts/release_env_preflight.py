"""Offline release safety gate. Never accesses cloud services or prints identifiers."""
import json
import os
import re
import sys

# Supabase project refs are 20 lowercase ASCII letters/digits.
PROJECT_REF = re.compile(r"^[a-z0-9]{20}$")
REQUIRED_EVIDENCE = {
    "staging_auth_e2e": "STAGING_AUTH_E2E_VERIFIED",
    "staging_rls_e2e": "STAGING_RLS_E2E_VERIFIED",
    "staging_migrations": "STAGING_MIGRATIONS_VERIFIED",
    "release_reviewed": "RELEASE_REVIEW_APPROVED",
}


def _valid_ref(value):
    return isinstance(value, str) and PROJECT_REF.fullmatch(value) is not None


def evaluate(settings):
    staging = settings.get("STAGING_PROJECT_REF")
    production = settings.get("PRODUCTION_PROJECT_REF")
    valid_refs = _valid_ref(staging) and _valid_ref(production)
    checks = {
        "valid_project_refs": valid_refs,
        "refs_present": bool(staging and production),
        "separate_staging": bool(valid_refs and staging != production),
        "valid_target": settings.get("RELEASE_TARGET") == "staging",
        "staging_mode": settings.get("RELEASE_TARGET") == "staging",
        "production_locked": settings.get("PRODUCTION_APPROVED") != "yes",
    }
    checks["safe_for_staging"] = all(checks.values())
    return checks


def release_decision(settings):
    checks = evaluate(settings)
    checks.update({
        name: settings.get(key) == "yes"
        for name, key in REQUIRED_EVIDENCE.items()
    })
    return {
        "ready_for_release_review": all(checks.values()),
        "checks": checks,
    }


def main():
    safety = evaluate(os.environ)
    readiness = release_decision(os.environ)
    # Only booleans; project refs, DB URLs and tokens must never be logged.
    print(json.dumps({
        "staging_preflight_passed": safety["safe_for_staging"],
        "ready_for_release_review": readiness["ready_for_release_review"],
        "checks": readiness["checks"],
    }, sort_keys=True))
    return 0 if safety["safe_for_staging"] else 1


if __name__ == "__main__":
    sys.exit(main())
