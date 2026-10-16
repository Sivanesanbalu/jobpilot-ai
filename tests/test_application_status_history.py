from pathlib import Path
from fastapi.testclient import TestClient
from app import app

SQL=Path(__file__).resolve().parents[1].joinpath("supabase/migrations/20261016200000_application_status_history.sql").read_text()

def test_status_history_is_owner_scoped_and_append_only():
    assert "enable row level security" in SQL
    assert "revoke all on public.application_status_events from anon,authenticated" in SQL
    assert "grant select on public.application_status_events to authenticated" in SQL
    assert "create trigger application_status_audit" in SQL
    assert "old.status is distinct from new.status" in SQL

def test_status_history_dashboard_scopes_to_authenticated_user():
    html=TestClient(app).get("/").text
    assert 'id="cloudStatusHistoryBtn"' in html
    assert 'id="cloudStatusHistory"' in html
    assert 'sb.from("application_status_events").select(' in html
    assert '.eq("user_id",user.id)' in html
    assert 'async function cloudStatusHistory()' in html
