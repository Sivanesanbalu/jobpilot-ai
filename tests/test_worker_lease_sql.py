from pathlib import Path

SQL = Path(__file__).resolve().parents[1].joinpath("supabase/migrations/20261015235000_worker_leases.sql").read_text()

def test_lease_claim_is_atomic():
    assert "on conflict(saved_search_id) do update" in SQL
    assert "expires_at < clock_timestamp()" in SQL
    assert "return found;" in SQL

def test_release_requires_lease_token():
    assert "saved_search_id=p_search_id and lease_token=p_token" in SQL

def test_lease_functions_private_and_no_browser_execute():
    assert "create schema if not exists jobpilot_private" in SQL
    assert "security invoker" in SQL
    assert "revoke all on schema jobpilot_private from public, anon, authenticated" in SQL
    assert SQL.count("from public,anon,authenticated") == 2
