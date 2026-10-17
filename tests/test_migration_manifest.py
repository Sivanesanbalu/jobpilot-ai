from scripts.check_migration_manifest import validate, REQUIRED, MIGRATIONS

def test_required_migration_files_exist():
    assert all((MIGRATIONS / name).is_file() for name in REQUIRED)

def test_migration_manifest_has_no_filename_drift():
    assert validate() == []
