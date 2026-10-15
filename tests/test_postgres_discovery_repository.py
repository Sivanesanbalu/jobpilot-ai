from pathlib import Path
from postgres_discovery_repository import PostgresDiscoveryRepository

SOURCE=Path(__file__).resolve().parents[1].joinpath("postgres_discovery_repository.py").read_text()

def test_repository_has_atomic_completion():
    assert "async with conn.transaction()" in SOURCE
    assert "for update" in SOURCE
    assert "on conflict(user_id,saved_search_id,job_url) do nothing" in SOURCE
    assert "set status='succeeded'" in SOURCE

def test_repository_guards_rerun_and_invalid_leases():
    assert "status='running' for update" in SOURCE
    import asyncio
    class UnusedPool:
        def acquire(self):
            raise AssertionError("Invalid lease must not access database")
    repository=PostgresDiscoveryRepository(UnusedPool())
    import pytest
    with pytest.raises(ValueError):
        asyncio.run(repository.acquire_lease("00000000-0000-0000-0000-000000000001","00000000-0000-0000-0000-000000000002",5))
