from pathlib import Path

SQL=Path(__file__).resolve().parents[1].joinpath("supabase/migrations/20261015224400_job_discovery_state.sql").read_text()

def test_all_discovery_tables_have_rls():
    for table in ("saved_searches","discovery_runs","job_notifications"):
        assert f"alter table public.{table} enable row level security" in SQL
        assert f"revoke all on public.{table} from anon" in SQL

def test_child_tables_enforce_same_user_as_saved_search():
    assert SQL.count("foreign key(saved_search_id,user_id) references public.saved_searches(id,user_id)")==2

def test_user_notifications_allow_read_state_only():
    assert "grant update(read_at) on public.job_notifications to authenticated" in SQL
    assert "grant select,update on public.job_notifications to authenticated" not in SQL

def test_worker_owned_tables_not_writable_from_browser():
    assert "grant select on public.discovery_runs to authenticated" in SQL
    assert "grant select on public.job_notifications to authenticated" in SQL

def test_discovery_leases_are_worker_only():
    assert "create table if not exists public.discovery_worker_leases" in SQL
    assert "alter table public.discovery_worker_leases enable row level security" in SQL
    assert "revoke all on public.discovery_worker_leases from anon, authenticated" in SQL
