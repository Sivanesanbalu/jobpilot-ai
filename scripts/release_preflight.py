"""Offline, secret-free release preflight. Never contacts or changes production."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from worker_runtime import WorkerSettings

ROOT=Path(__file__).resolve().parents[1]
REQUIRED_MIGRATIONS=(
 "20261015224400_job_discovery_state.sql",
 "20261015235000_worker_leases.sql",
 "20261016193000_application_drafts.sql",
 "20261016194500_draft_tracker_link.sql",
 "20261016200000_application_status_history.sql",
)

def check_release_files():
    for name in REQUIRED_MIGRATIONS:
        if not (ROOT/"supabase/migrations"/name).is_file():
            raise RuntimeError(f"Missing required migration: {name}")
    if not (ROOT/"docs/PRODUCTION_RELEASE_GATE.md").is_file():
        raise RuntimeError("Release gate document missing")
    for file in ("scripts/staging_schema_preflight.sql","tests/postgres/integration.py"):
        if not (ROOT/file).is_file():
            raise RuntimeError(f"Missing staging validation: {file}")

def check_worker_config():
    # Synthetic credentials only; production secrets must not be read in CI.
    valid={"JOBPILOT_WORKER_DATABASE_URL":"postgresql://worker:synthetic-only@staging.example.invalid:5432/jobpilot?sslmode=require","JOBPILOT_POOL_MIN":"1","JOBPILOT_POOL_MAX":"5"}
    assert WorkerSettings.from_env(valid).pool_max==5
    unsafe=({**valid,"JOBPILOT_WORKER_DATABASE_URL":"postgresql://worker:synthetic-only@staging.example.invalid/jobpilot?sslmode=disable"},
            {**valid,"JOBPILOT_POOL_MIN":"10","JOBPILOT_POOL_MAX":"2"},
            {**valid,"JOBPILOT_WORKER_DATABASE_URL":"postgresql://worker:synthetic-only@localhost/jobpilot"})
    for env in unsafe:
        try:
            WorkerSettings.from_env(env)
        except ValueError:
            continue
        raise RuntimeError("Unsafe worker config unexpectedly accepted")

def main():
    check_release_files()
    check_worker_config()
    print("Offline release configuration preflight passed. Production release remains BLOCKED pending staging and approval.")

if __name__=="__main__":
    main()
