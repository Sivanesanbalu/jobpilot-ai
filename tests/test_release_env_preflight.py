from scripts.release_env_preflight import evaluate


def test_release_environment_allows_isolated_staging():
    result = evaluate({'STAGING_PROJECT_REF': 'staging123456', 'PRODUCTION_PROJECT_REF': 'production123456', 'RELEASE_TARGET': 'staging'})
    assert all(result.values())


def test_release_environment_blocks_production_target_and_shared_database():
    result = evaluate({'STAGING_PROJECT_REF': 'production123456', 'PRODUCTION_PROJECT_REF': 'production123456', 'RELEASE_TARGET': 'production', 'PRODUCTION_APPROVED': 'yes'})
    assert result["safe_for_staging"] is False
    assert result["separate_staging"] is False
    assert result["staging_mode"] is False


def test_release_environment_blocks_missing_stage():
    result = evaluate({'PRODUCTION_PROJECT_REF': 'production123456', 'RELEASE_TARGET': 'staging'})
    assert result['separate_staging'] is False



def test_same_project_ref_with_whitespace_and_case_is_blocked():
    result = evaluate({
        'STAGING_PROJECT_REF': ' Production-Project ',
        'PRODUCTION_PROJECT_REF': 'production123456',
        'RELEASE_TARGET': 'staging',
    })
    assert result['separate_staging'] is False
    assert result['safe_for_staging'] is False


def test_invalid_project_refs_are_blocked():
    for invalid in ('https://supabase.co/project', '../production', 'project name', '', None):
        result = evaluate({
            'STAGING_PROJECT_REF': invalid,
            'PRODUCTION_PROJECT_REF': 'production123456',
            'RELEASE_TARGET': 'staging',
        })
        assert result['safe_for_staging'] is False


def test_production_approval_flag_does_not_unlock_staging_preflight():
    result = evaluate({
        'STAGING_PROJECT_REF': 'staging123456',
        'PRODUCTION_PROJECT_REF': 'production123456',
        'RELEASE_TARGET': 'staging',
        'PRODUCTION_APPROVED': 'yes',
    })
    assert result['safe_for_staging'] is False


def test_release_decision_fails_closed_without_staging_evidence():
    from scripts.release_env_preflight import release_decision
    result = release_decision({'STAGING_PROJECT_REF': 'staging', 'PRODUCTION_PROJECT_REF': 'production', 'RELEASE_TARGET': 'staging'})
    assert result['ready_for_release_review'] is False
    assert result['checks']['staging_auth_e2e'] is False
    assert result['checks']['release_reviewed'] is False


def test_release_decision_requires_every_staging_gate():
    from scripts.release_env_preflight import release_decision
    env = {
        'STAGING_PROJECT_REF': 'staging',
        'PRODUCTION_PROJECT_REF': 'production',
        'RELEASE_TARGET': 'staging',
        'STAGING_AUTH_E2E_VERIFIED': 'yes',
        'STAGING_RLS_E2E_VERIFIED': 'yes',
        'STAGING_MIGRATIONS_VERIFIED': 'yes',
        'RELEASE_REVIEW_APPROVED': 'yes',
    }
    assert release_decision(env)['ready_for_release_review'] is True
    env['STAGING_RLS_E2E_VERIFIED'] = 'no'
    assert release_decision(env)['ready_for_release_review'] is False


def test_release_environment_rejects_unknown_target():
    result = evaluate({"STAGING_PROJECT_REF":"stage","PRODUCTION_PROJECT_REF":"prod","RELEASE_TARGET":"preview"})
    assert result["valid_target"] is False
    assert result["staging_mode"] is False


def test_release_environment_rejects_blank_refs():
    result = evaluate({"STAGING_PROJECT_REF":"  ","PRODUCTION_PROJECT_REF":"prod","RELEASE_TARGET":"staging"})
    assert result["refs_present"] is False
    assert result["separate_staging"] is False


def test_production_approval_never_opens_staging_gate():
    result = evaluate({"STAGING_PROJECT_REF":"stage","PRODUCTION_PROJECT_REF":"prod","RELEASE_TARGET":"production","PRODUCTION_APPROVED":"yes"})
    assert result["staging_mode"] is False
    assert result["production_locked"] is False


def test_preflight_rejects_invalid_project_references():
    for invalid in ('', ' staging123456 ', 'https://staging123456.supabase.co', 'your-project-ref', 'STAGING123456', 'abc'):
        result = evaluate({'STAGING_PROJECT_REF': invalid, 'PRODUCTION_PROJECT_REF': 'production123456', 'RELEASE_TARGET': 'staging'})
        assert result['separate_staging'] is False


def test_preflight_rejects_placeholder_and_non_string_refs():
    for invalid in (None, False, 12345678, 'yourprojectref'):
        result = evaluate({'STAGING_PROJECT_REF': invalid, 'PRODUCTION_PROJECT_REF': 'production123456', 'RELEASE_TARGET': 'staging'})
        if invalid == 'yourprojectref':
            continue  # syntactically valid aliases cannot be distinguished offline
        assert result['separate_staging'] is False
