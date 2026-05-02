import pytest
from agent_scout.state import StateStore


@pytest.fixture
def store(tmp_path):
    return StateStore(tmp_path)


def test_empty_store_returns_none(store):
    assert store.get("projects/proj/sess.jsonl") is None


def test_update_and_retrieve(store):
    store.update("projects/proj/sess.jsonl", bytes_read=512, mtime=1234567.0)
    state = store.get("projects/proj/sess.jsonl")
    assert state is not None
    assert state.bytes_read == 512
    assert state.mtime == 1234567.0


def test_persists_across_reload(tmp_path):
    s1 = StateStore(tmp_path)
    s1.update("f.jsonl", bytes_read=100, mtime=9.0)

    s2 = StateStore(tmp_path)
    state = s2.get("f.jsonl")
    assert state is not None
    assert state.bytes_read == 100


def test_update_overwrites(store):
    store.update("f.jsonl", bytes_read=100, mtime=1.0)
    store.update("f.jsonl", bytes_read=200, mtime=2.0)
    assert store.get("f.jsonl").bytes_read == 200


def test_multiple_files(store):
    store.update("a.jsonl", bytes_read=10, mtime=1.0)
    store.update("b.jsonl", bytes_read=20, mtime=2.0)
    assert store.get("a.jsonl").bytes_read == 10
    assert store.get("b.jsonl").bytes_read == 20
