"""Offline migration-manifest drift check. Does not connect to a database."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "supabase" / "migrations"
REQUIRED = (
    "20261015224400_job_discovery_state.sql",
    "20261015235000_worker_leases.sql",
    "20261016193000_application_drafts.sql",
    "20261016194500_draft_tracker_link.sql",
    "20261016200000_application_status_history.sql",
)

def validate():
    problems = []
    files = sorted(MIGRATIONS.glob("*.sql"))
    versions = {}
    for path in files:
        if not re.fullmatch(r"\d{14}_[a-z0-9_]+\.sql", path.name):
            problems.append("Invalid migration filename: " + path.name)
        version = path.name.split("_", 1)[0]
        if version in versions:
            problems.append("Duplicate migration timestamp: " + version)
        versions[version] = path
        if not path.read_text(encoding="utf-8").strip():
            problems.append("Empty migration: " + path.name)
    for name in REQUIRED:
        if not (MIGRATIONS / name).is_file():
            problems.append("Missing required migration: " + name)
    return problems

if __name__ == "__main__":
    for problem in validate():
        print("BLOCK:", problem)
    raise SystemExit(bool(validate()))
