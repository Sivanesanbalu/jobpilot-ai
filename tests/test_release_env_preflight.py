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
