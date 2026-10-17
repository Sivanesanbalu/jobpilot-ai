"""Offline release-target safety checks. Never reads or emits credentials."""

import json
import os
import sys


def evaluate(settings):
    staging = settings.get("STAGING_PROJECT_REF", "").strip()
    production = settings.get("PRODUCTION_PROJECT_REF", "").strip()
    checks = {
        "separate_staging": bool(staging and production and staging != production),
        "staging_mode": settings.get("RELEASE_TARGET") == "staging",
        "production_locked": settings.get("PRODUCTION_APPROVED") != "yes",
    }
    return checks


def main():
    checks = evaluate(os.environ)
    allowed = all(checks.values())
    # Output boolean checks only: never print project refs, tokens or URLs.
    print(json.dumps({"staging_preflight_passed": allowed, "checks": checks}, sort_keys=True))
    return 0 if allowed else 1


if __name__ == "__main__":
    sys.exit(main())
