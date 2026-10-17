from scripts.release_env_preflight import evaluate


def test_release_environment_allows_isolated_staging():
    result = evaluate({'STAGING_PROJECT_REF': 'staging-project', 'PRODUCTION_PROJECT_REF': 'production-project', 'RELEASE_TARGET': 'staging'})
    assert all(result.values())


def test_release_environment_blocks_production_target_and_shared_database():
    result = evaluate({'STAGING_PROJECT_REF': 'production-project', 'PRODUCTION_PROJECT_REF': 'production-project', 'RELEASE_TARGET': 'production', 'PRODUCTION_APPROVED': 'yes'})
    assert not any(result.values())


def test_release_environment_blocks_missing_stage():
    result = evaluate({'PRODUCTION_PROJECT_REF': 'production-project', 'RELEASE_TARGET': 'staging'})
    assert result['separate_staging'] is False



def test_same_project_ref_with_whitespace_and_case_is_blocked():
    result = evaluate({
        'STAGING_PROJECT_REF': ' Production-Project ',
        'PRODUCTION_PROJECT_REF': 'production-project',
        'RELEASE_TARGET': 'staging',
    })
    assert result['separate_staging'] is False
    assert result['safe_for_staging'] is False


def test_invalid_project_refs_are_blocked():
    for invalid in ('https://supabase.co/project', '../production', 'project name', '', None):
        result = evaluate({
            'STAGING_PROJECT_REF': invalid,
            'PRODUCTION_PROJECT_REF': 'production-project',
            'RELEASE_TARGET': 'staging',
        })
        assert result['safe_for_staging'] is False


def test_production_approval_flag_does_not_unlock_staging_preflight():
    result = evaluate({
        'STAGING_PROJECT_REF': 'staging-project',
        'PRODUCTION_PROJECT_REF': 'production-project',
        'RELEASE_TARGET': 'staging',
        'PRODUCTION_APPROVED': 'yes',
    })
    assert result['safe_for_staging'] is False
