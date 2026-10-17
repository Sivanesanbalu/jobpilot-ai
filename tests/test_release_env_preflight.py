"""Regression tests for a fail-closed, strictly offline staging release gate."""
import json
import os
import subprocess
import sys

from scripts.release_env_preflight import evaluate, release_decision

STAGE = "abcdefghijklmnopqrst"
PROD = "uvwxyzabcdefghijklmn"


def settings(**overrides):
    return dict(STAGING_PROJECT_REF=STAGE, PRODUCTION_PROJECT_REF=PROD,
                RELEASE_TARGET="staging", PRODUCTION_APPROVED="no", **overrides)


def test_isolated_staging_is_only_safe_target():
    state = evaluate(settings())
    assert state["safe_for_staging"]
    assert state["separate_staging"] and state["valid_project_refs"]
    assert state["production_locked"]


def test_prod_approval_and_prod_target_are_always_blocked():
    state = evaluate({**settings(), "PRODUCTION_APPROVED": "yes", "RELEASE_TARGET": "production"})
    assert not state["safe_for_staging"]
    assert not state["staging_mode"]
    assert not state["production_locked"]


def test_duplicate_project_ref_fails_closed():
    state = evaluate({**settings(), "STAGING_PROJECT_REF": PROD})
    assert not state["separate_staging"]
    assert not state["safe_for_staging"]


def test_invalid_project_refs_never_pass():
    for invalid in ("", None, False, 123, " ", "staging", "STAGINGPROJECT1234567",
                    "abc-1234567890abcdef", "https://a.supabase.co", "../production",
                    " abcdefghijklmnopqrst", "abcdefghijklmnopqrst "):
        state = evaluate({**settings(), "STAGING_PROJECT_REF": invalid})
        assert not state["valid_project_refs"]
        assert not state["safe_for_staging"]


def test_unknown_target_fails_closed():
    assert not evaluate({**settings(), "RELEASE_TARGET": "preview"})["valid_target"]


def test_release_evidence_is_required_without_treating_ci_as_supabase_e2e():
    assert not release_decision(settings())["ready_for_release_review"]
    evidence = dict(STAGING_AUTH_E2E_VERIFIED="yes", STAGING_RLS_E2E_VERIFIED="yes",
                    STAGING_MIGRATIONS_VERIFIED="yes", RELEASE_REVIEW_APPROVED="yes")
    assert release_decision({**settings(), **evidence})["ready_for_release_review"]
    for key in evidence:
        incomplete = {**settings(), **evidence, key: "no"}
        assert not release_decision(incomplete)["ready_for_release_review"]


def test_cli_is_private_and_returns_nonzero_for_unsafe_environment():
    env = {**os.environ, **settings(), "SECRET_EXAMPLE": "do-not-print"}
    cmd = [sys.executable, "-m", "scripts.release_env_preflight"]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["staging_preflight_passed"] is True
    assert data["ready_for_release_review"] is False
    assert STAGE not in result.stdout and PROD not in result.stdout
    assert "do-not-print" not in result.stdout
    env["RELEASE_TARGET"] = "production"
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert json.loads(result.stdout)["staging_preflight_passed"] is False


def test_release_environment_rejects_whitespace_and_invalid_project_refs():
    bad = evaluate({'STAGING_PROJECT_REF': 'stage project!', 'PRODUCTION_PROJECT_REF': 'production-project', 'RELEASE_TARGET': 'staging'})
    assert bad['separate_staging'] is False
    padded = evaluate({'STAGING_PROJECT_REF': ' production-project ', 'PRODUCTION_PROJECT_REF': 'production-project', 'RELEASE_TARGET': 'staging'})
    assert padded['separate_staging'] is False


def test_release_environment_does_not_unlock_production_with_mixed_case_approval():
    result = evaluate({'STAGING_PROJECT_REF': 'stage-project', 'PRODUCTION_PROJECT_REF': 'production-project', 'RELEASE_TARGET': ' STAGING ', 'PRODUCTION_APPROVED': ' YES '})
    assert result['production_locked'] is False
    assert result['staging_mode'] is True
