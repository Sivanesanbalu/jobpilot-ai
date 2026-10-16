from pathlib import Path
from fastapi.testclient import TestClient
from app import app

SQL=Path(__file__).resolve().parents[1].joinpath("supabase/migrations/20261016193000_application_drafts.sql").read_text()

def test_cloud_draft_tables_have_owner_rls():
    for name in ("application_drafts","application_approval_events"):
        assert f"alter table public.{name} enable row level security" in SQL
        assert f"revoke all on public.{name} from anon" in SQL
        assert f"auth.uid())=user_id" in SQL

def test_approval_events_are_append_only_and_cross_user_restricted():
    assert "grant select,insert on public.application_approval_events to authenticated" in SQL
    assert "foreign key (draft_id,user_id)" in SQL
    assert "grant select,insert,update,delete on public.application_approval_events" not in SQL

def test_cloud_dashboard_has_scoped_crud_and_no_auto_submit():
    html=TestClient(app).get("/").text
    assert 'id="cloudSaveDraftBtn"' in html
    assert 'id="cloudLoadDraftsBtn"' in html
    assert 'sb.from("application_drafts").insert(' in html
    assert 'sb.from("application_drafts").delete()' in html
    assert '.eq("user_id",user.id)' in html
    assert 'submission_status:"NOT_SUBMITTED"' in html
