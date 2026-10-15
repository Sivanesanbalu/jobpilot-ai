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
    def __init__(self, healthy=True):
        self.healthy=healthy
        self.closed=False
    @asynccontextmanager
    async def acquire(self):
        yield self
    async def fetchval(self, query):
        if not self.healthy:
            raise OSError("database unreachable")
        return 1
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
