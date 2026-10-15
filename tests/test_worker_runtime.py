import asyncio
import pytest
from contextlib import asynccontextmanager
from worker_runtime import WorkerSettings, WorkerRuntime

def test_worker_requires_database_url():
    with pytest.raises(ValueError):
        WorkerSettings.from_env({})
    with pytest.raises(ValueError):
        WorkerSettings.from_env({"JOBPILOT_WORKER_DATABASE_URL":"https://example.com"})

def test_pool_settings_bounded():
    env={"JOBPILOT_WORKER_DATABASE_URL":"postgresql://user:pass@db.example.com/db","JOBPILOT_POOL_MAX":"21"}
    with pytest.raises(ValueError):
        WorkerSettings.from_env(env)

def test_insecure_local_database_requires_opt_in():
    with pytest.raises(ValueError):
        WorkerSettings.from_env({"JOBPILOT_WORKER_DATABASE_URL":"postgresql://u:p@localhost/db"})

class FakePool:
    def __init__(self, healthy=True, migrations=True):
        self.healthy=healthy
        self.migrations=migrations
        self.closed=False
    @asynccontextmanager
    async def acquire(self):
        yield self
    async def fetchval(self, query):
        if not self.healthy:
            raise OSError("database unreachable")
        return 1
    async def fetchrow(self, query):
        return {key:self.migrations for key in ("searches","runs","notifications","leases","acquire","release")}
    async def close(self):
        self.closed=True

def test_runtime_start_health_and_graceful_close():
    pool=FakePool()
    async def factory(**kwargs):
        assert kwargs["ssl"]=="require"
        return pool
    runtime=WorkerRuntime(WorkerSettings("postgresql://u:p@db.example.com/db"),factory)
    asyncio.run(runtime.start())
    assert asyncio.run(runtime.health())["ok"] is True
    assert runtime.repository().pool is pool
    asyncio.run(runtime.close())
    assert pool.closed is True

def test_failed_start_closes_pool():
    pool=FakePool(healthy=False)
    async def factory(**kwargs):
        return pool
    runtime=WorkerRuntime(WorkerSettings("postgresql://u:p@db.example.com/db"),factory)
    with pytest.raises(OSError):
        asyncio.run(runtime.start())
    assert pool.closed is True
    assert runtime.pool is None

def test_rejects_unsafe_sslmode_even_with_old_override():
    for sslmode in ("disable", "allow", "prefer"):
        env={"JOBPILOT_WORKER_DATABASE_URL":f"postgresql://u:p@db.example.com/db?sslmode={sslmode}",
             "JOBPILOT_ALLOW_INSECURE_DB":"1"}
        with pytest.raises(ValueError, match="TLS"):
            WorkerSettings.from_env(env)

def test_requires_database_credentials():
    with pytest.raises(ValueError,match="credentials"):
        WorkerSettings.from_env({"JOBPILOT_WORKER_DATABASE_URL":"postgresql://db.example.com/db"})

def test_missing_database_migrations_prevent_worker_start():
    pool=FakePool(migrations=False)
    async def factory(**kwargs):
        return pool
    runtime=WorkerRuntime(WorkerSettings("postgresql://u:p@db.example.com/db"),factory)
    with pytest.raises(RuntimeError, match="Worker migrations are missing"):
        asyncio.run(runtime.start())
    assert runtime.pool is None
    assert pool.closed is True
