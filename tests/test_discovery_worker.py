import asyncio
import pytest
from discovery_worker import fetch_with_retry, run_once

def test_worker_retries_transient_failure_then_persists(tmp_path):
    calls=[]
    async def fetcher(query):
        calls.append(query)
        if len(calls)<3:
            raise TimeoutError("temporary")
        return [{"title":"AI Engineer","url":"https://example.com/jobs/123"}]
    path=tmp_path/"state.json"
    one=asyncio.run(run_once(path,"ai","AI engineer",fetcher))
    assert one["count"]==1
    assert one["notifications_sent"] is False
    two=asyncio.run(run_once(path,"ai","AI engineer",fetcher))
    assert two["count"]==0
    assert len(calls)==4

def test_worker_does_not_advance_state_on_failure(tmp_path):
    async def failing(query):
        raise ConnectionError("no connection")
    path=tmp_path/"state.json"
    with pytest.raises(ConnectionError):
        asyncio.run(run_once(path,"ai","AI engineer",failing))
    assert not path.exists()

def test_worker_rejects_bad_attempts():
    async def fetcher(query):
        return []
    with pytest.raises(ValueError):
        asyncio.run(fetch_with_retry(fetcher,"test",attempts=0))
