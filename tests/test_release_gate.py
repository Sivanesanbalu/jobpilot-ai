from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GATE=(ROOT/"docs/PRODUCTION_RELEASE_GATE.md").read_text()
MIGRATIONS=ROOT/"supabase/migrations"

def test_release_gate_tracks_existing_ordered_migrations():
    sequence=[
        "20261015224400_job_discovery_state.sql",
        "20261015235000_worker_leases.sql",
        "20261016193000_application_drafts.sql",
        "20261016194500_draft_tracker_link.sql",
        "20261016200000_application_status_history.sql",
    ]
    assert sequence==sorted(sequence)
    for name in sequence:
        assert (MIGRATIONS/name).is_file()
        assert name in GATE

def test_release_gate_keeps_production_blocked_until_explicit_approval():
    assert "NOT APPROVED FOR PRODUCTION RELEASE" in GATE
    assert "separate staging Supabase project" in GATE
    assert "explicit approval" in GATE
    assert "no implicit authorization" in GATE
