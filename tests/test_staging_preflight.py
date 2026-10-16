from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREFLIGHT=(ROOT/"scripts/staging_schema_preflight.sql").read_text()

def test_staging_preflight_requires_all_new_tables_and_rls():
    for name in ("application_drafts","application_approval_events","application_status_events","saved_searches","discovery_worker_leases"):
        assert "'public."+name+"'" in PREFLIGHT
    assert "relrowsecurity" in PREFLIGHT
    assert "raise exception 'RLS disabled" in PREFLIGHT

def test_preflight_rejects_audit_writer_privileges_and_missing_triggers():
    assert "has_table_privilege('authenticated','public.application_approval_events','INSERT')" in PREFLIGHT
    assert "has_table_privilege('authenticated','public.application_status_events','INSERT')" in PREFLIGHT
    assert "application_draft_review_audit" in PREFLIGHT
    assert "application_status_audit" in PREFLIGHT

def test_preflight_does_not_modify_schema():
    lowered=PREFLIGHT.lower()
    assert "create table" not in lowered
    assert "alter table" not in lowered
    assert "drop table" not in lowered
