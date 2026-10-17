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

def test_approval_audit_is_database_generated():
    assert "revoke insert on public.application_approval_events from authenticated" in SQL
    assert "create trigger application_draft_review_audit" in SQL
    assert "security definer set search_path = ''" in SQL
    assert "review_approved" in SQL and "review_revoked" in SQL

def test_review_controls_and_history_are_account_scoped():
    html=TestClient(app).get("/").text
    assert 'id="cloudApprovalHistoryBtn"' in html
    assert 'async function setCloudDraftApproval(' in html
    assert 'async function cloudApprovalHistory()' in html
    assert '.from("application_approval_events").select(' in html
    assert 'Review status saved. NOT SUBMITTED.' in html

def test_draft_link_migration_and_safe_tracker_action():
    migration=Path(__file__).resolve().parents[1].joinpath("supabase/migrations/20261016194500_draft_tracker_link.sql").read_text()
    assert "add column if not exists apply_url text" in migration
    assert "application_drafts_apply_url_https" in migration
    html=TestClient(app).get("/").text
    assert 'apply_url:applyUrl||null' in html
    assert 'track.textContent="Save to tracker"' in html
    assert 'status:"Saved"' in html
    assert 'status:"Applied"' not in html[html.index('track.textContent="Save to tracker"'):html.index('track.textContent="Save to tracker"')+900]
