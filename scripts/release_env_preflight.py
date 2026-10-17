"""Check release targets without connecting to external systems.

This is a local fail-closed preflight, not permission to run migrations.
"""
import re


_PROJECT_REF = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _reference(value):
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def evaluate(settings):
    staging = _reference(settings.get("STAGING_PROJECT_REF", ""))
    production = _reference(settings.get("PRODUCTION_PROJECT_REF", ""))
    staging_valid = bool(_PROJECT_REF.fullmatch(staging))
    production_valid = bool(_PROJECT_REF.fullmatch(production))
    separate = staging_valid and production_valid and staging != production
    staging_mode = settings.get("RELEASE_TARGET") == "staging"
    production_locked = settings.get("PRODUCTION_APPROVED") != "yes"
    return {
        "separate_staging": separate,
        "staging_mode": staging_mode,
        "production_locked": production_locked,
        "safe_for_staging": separate and staging_mode and production_locked,
    }
