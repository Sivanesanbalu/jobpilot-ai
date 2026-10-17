"""Offline, fail-closed staging release preflight; prints no project IDs or secrets."""
import json
import os
import re

REF = re.compile(r"^[a-z]{20}$")
EVIDENCE = ("STAGING_AUTH_E2E_VERIFIED", "STAGING_RLS_E2E_VERIFIED",
            "STAGING_MIGRATIONS_VERIFIED", "RELEASE_REVIEW_APPROVED")


def evaluate(settings):
    stage = settings.get("STAGING_PROJECT_REF")
    prod = settings.get("PRODUCTION_PROJECT_REF")
    valid = isinstance(stage, str) and isinstance(prod, str) and bool(REF.fullmatch(stage)) and bool(REF.fullmatch(prod))
    separate = bool(valid and stage != prod)
    target = settings.get("RELEASE_TARGET")
    staging_mode = target == "staging"
    locked = settings.get("PRODUCTION_APPROVED") != "yes"
    return {
        "valid_project_refs": bool(valid),
        "separate_staging": separate,
        "valid_target": target in ("staging", "production"),
        "staging_mode": staging_mode,
        "production_locked": locked,
        "safe_for_staging": separate and staging_mode and locked,
    }


def release_decision(settings):
    state = evaluate(settings)
    evidence = all(settings.get(key) == "yes" for key in EVIDENCE)
    return {
        "staging_preflight_passed": state["safe_for_staging"],
        "ready_for_release_review": state["safe_for_staging"] and evidence,
    }


if __name__ == "__main__":
    decision = release_decision(os.environ)
    print(json.dumps(decision))
    raise SystemExit(0 if decision["staging_preflight_passed"] else 1)
