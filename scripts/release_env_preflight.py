"""Check release targets without connecting to external systems."""

def evaluate(settings):
    staging = settings.get('STAGING_PROJECT_REF', '')
    production = settings.get('PRODUCTION_PROJECT_REF', '')
    return {
        'separate_staging': bool(staging and production and staging != production),
        'staging_mode': settings.get('RELEASE_TARGET') == 'staging',
        'production_locked': settings.get('PRODUCTION_APPROVED') != 'yes',
    }
