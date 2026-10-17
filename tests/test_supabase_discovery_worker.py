import asyncio
import pytest
from supabase_discovery_worker import process_search

class FakeRepository:
    def __init__(self):
        self.held=False
        self.finished=[]
        self.failed=[]
        self.released=[]
        self.search={"id":"s1","user_id":"u1","query":"AI engineer","is_enabled":True}
    async def acquire_lease(self,search_id,token,seconds):
        if self.held:return False
        self.held=True
        return True
    async def get_search(self,search_id):
        return self.search
    async def start_run(self,search):
        return "run1"
    async def complete_run(self,run_id,jobs,token):
        self.finished.append((run_id,jobs))
        return len(jobs)
    async def fail_run(self,run_id,error):
        self.failed.append((run_id,error))
    async def release_lease(self,search_id,token):
        self.released.append(search_id)
        self.held=False

def test_worker_deduplicates_and_releases():
    repo=FakeRepository()
    async def fetch(query):
        return [{"url":"https://example.com/a","title":"AI Engineer"},
                {"url":"https://example.com/a/","title":"Duplicate"}]
    result=asyncio.run(process_search(repo,fetch,"s1"))
    assert result["status"]=="succeeded"
    assert result["new_jobs"]==1
    assert len(repo.finished[0][1])==1
    assert repo.released==["s1"]

def test_worker_failure_marks_run_and_releases():
    repo=FakeRepository()
    async def fetch(query):
        raise ValueError("malformed feed")
    with pytest.raises(ValueError):
        asyncio.run(process_search(repo,fetch,"s1"))
    assert repo.failed[0][0]=="run1"
    assert repo.released==["s1"]

def test_busy_worker_does_not_fetch():
    repo=FakeRepository()
    repo.held=True
    async def fetch(query):
        raise AssertionError("should not fetch")
    result=asyncio.run(process_search(repo,fetch,"s1"))
    assert result["status"]=="busy"
    assert not repo.finished

def test_completion_receives_lease_token():
    repo=FakeRepository()
    async def fetch(query):
        return [{"url":"https://example.com/a","title":"AI Engineer"}]
    result=asyncio.run(process_search(repo,fetch,"s1"))
    assert result["status"]=="succeeded"
    assert repo.released==["s1"]

def test_original_fetch_error_survives_failed_status_write_and_release():
    class BrokenCleanup(FakeRepository):
        async def fail_run(self,run_id,error):
            raise RuntimeError("status storage unavailable")
        async def release_lease(self,search_id,token):
            raise RuntimeError("lease service unavailable")
    repo=BrokenCleanup()
    async def failing_fetch(query):
        raise ValueError("original job feed error")
    with pytest.raises(ValueError,match="original job feed error") as exc:
        asyncio.run(process_search(repo,failing_fetch,"s1"))
    assert "Failed to record" in " ".join(exc.value.__notes__)
    assert "Worker lease release failed" in " ".join(exc.value.__notes__)

def test_release_failure_after_success_is_not_silent():
    class BrokenRelease(FakeRepository):
        async def release_lease(self,search_id,token):
            raise RuntimeError("lease service unavailable")
    repo=BrokenRelease()
    async def fetch(query):
        return []
    with pytest.raises(RuntimeError,match="lease service unavailable"):
        asyncio.run(process_search(repo,fetch,"s1"))

def test_concurrent_search_attempts_only_one_acquires_lease():
    repo=FakeRepository()
    started=asyncio.Event()
    proceed=asyncio.Event()
    calls=[]
    async def fetch(query):
        calls.append(query)
        started.set()
        await proceed.wait()
        return [{"url":"https://example.com/a","title":"AI Engineer"}]
    async def scenario():
        first=asyncio.create_task(process_search(repo,fetch,"s1"))
        await started.wait()
        second=await process_search(repo,fetch,"s1")
        assert second=={"status":"busy","new_jobs":0}
        proceed.set()
        result=await first
        return result
    result=asyncio.run(scenario())
    assert result["status"]=="succeeded"
    assert len(calls)==1
    assert len(repo.finished)==1
    assert repo.released==["s1"]
