from discovery_state import read_state, atomic_write, update_search

def test_discovery_state_round_trip(tmp_path):
    path=tmp_path/"searches.json"
    assert read_state(path)=={"searches":{}}
    initial={"searches":{}}
    jobs=[{"url":"https://example.com/jobs/1","title":"Engineer"}]
    updated,fresh=update_search(initial,"ai","AI engineer",jobs)
    assert len(fresh)==1
    atomic_write(path,updated)
    loaded=read_state(path)
    newer,second=update_search(loaded,"ai","AI engineer",jobs)
    assert second==[]
    assert newer==loaded

def test_independent_searches():
    base={"searches":{}}
    one,_=update_search(base,"ai","AI engineer",[{"url":"https://example.com/1"}])
    two,fresh=update_search(one,"frontend","Frontend developer",[{"url":"https://example.com/1"}])
    assert len(fresh)==1
    assert set(two["searches"])=={"ai","frontend"}
    assert base=={"searches":{}}

def test_invalid_search_rejected():
    import pytest
    with pytest.raises(ValueError):
        update_search({"searches":{}},"","AI engineer",[])
