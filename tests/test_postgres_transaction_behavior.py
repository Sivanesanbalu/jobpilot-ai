"""Executable transaction behavior tests using an in-memory asyncpg-compatible fake."""
import asyncio
from contextlib import asynccontextmanager
from uuid import UUID
import pytest
from postgres_discovery_repository import PostgresDiscoveryRepository

RUN=UUID("00000000-0000-0000-0000-000000000011")
SEARCH=UUID("00000000-0000-0000-0000-000000000012")
USER=UUID("00000000-0000-0000-0000-000000000013")
TOKEN=UUID("00000000-0000-0000-0000-000000000014")

class FakeConnection:
    def __init__(self, *, lease=True, fail_on_insert=False):
        self.lease=lease
        self.fail_on_insert=fail_on_insert
        self.notifications=[]
        self.status="running"
        self.in_transaction=False
    @asynccontextmanager
    async def transaction(self):
        old=(self.notifications.copy(),self.status)
        self.in_transaction=True
        try:
            yield
        except Exception:
            self.notifications,self.status=old
            raise
        finally:
            self.in_transaction=False
    async def fetchrow(self, sql, *args):
        assert self.in_transaction
        return {"user_id":USER,"saved_search_id":SEARCH} if self.status=="running" else None
    async def fetchval(self, sql, *args):
        assert self.in_transaction
        if "discovery_worker_leases" in sql:
            assert args==(SEARCH,TOKEN)
            return 1 if self.lease else None
        if self.fail_on_insert:
            raise RuntimeError("insertion failed")
        assert args[0:2]==(USER,SEARCH)
        url=args[2]
        if url in self.notifications:
            return None
        self.notifications.append(url)
        return UUID("00000000-0000-0000-0000-000000000020")
    async def execute(self, sql, *args):
        assert self.in_transaction
        assert "status='succeeded'" in sql
        self.status="succeeded"

class FakePool:
    def __init__(self,connection):
        self.connection=connection
    @asynccontextmanager
    async def acquire(self):
        yield self.connection

def jobs():
    return [{"job_url":"https://example.com/1","title":"Engineer","company":"Example"}]

def test_completion_commits_once_and_rejects_second_finalize():
    conn=FakeConnection()
    repo=PostgresDiscoveryRepository(FakePool(conn))
    assert asyncio.run(repo.complete_run(RUN,jobs(),TOKEN))==1
    assert conn.status=="succeeded"
    with pytest.raises(ValueError):
        asyncio.run(repo.complete_run(RUN,jobs(),TOKEN))
    assert conn.notifications==["https://example.com/1"]

def test_stale_lease_cannot_commit_notifications():
    conn=FakeConnection(lease=False)
    repo=PostgresDiscoveryRepository(FakePool(conn))
    with pytest.raises(RuntimeError,match="lease expired"):
        asyncio.run(repo.complete_run(RUN,jobs(),TOKEN))
    assert conn.notifications==[]
    assert conn.status=="running"

def test_failed_insert_rolls_back_completion():
    conn=FakeConnection(fail_on_insert=True)
    repo=PostgresDiscoveryRepository(FakePool(conn))
    with pytest.raises(RuntimeError,match="insertion failed"):
        asyncio.run(repo.complete_run(RUN,jobs(),TOKEN))
    assert conn.notifications==[]
    assert conn.status=="running"
