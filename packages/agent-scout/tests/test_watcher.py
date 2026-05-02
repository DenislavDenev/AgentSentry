import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from agent_scout.state import StateStore
from agent_scout.watcher import _JournalHandler


@pytest.fixture
def data_dir(tmp_path):
    projects = tmp_path / "projects" / "test-proj"
    projects.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def state(tmp_path):
    return StateStore(tmp_path / "state")


@pytest.fixture
def emitter():
    m = MagicMock()
    m.emit.return_value = True
    return m


@pytest.fixture
def handler(data_dir, state, emitter):
    return _JournalHandler(data_dir, state, emitter)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("ab") as f:
        for r in records:
            f.write(json.dumps(r).encode() + b"\n")


def _record(uuid="u1", session="s1"):
    return {
        "uuid": uuid,
        "type": "assistant",
        "sessionId": session,
        "timestamp": "2025-01-01T00:00:00Z",
        "message": {"id": "m1", "model": "claude-sonnet-4-6", "content": [], "usage": {}},
    }


def test_processes_new_file(data_dir, handler):
    p = data_dir / "projects" / "test-proj" / "sess.jsonl"
    _write_jsonl(p, [_record()])
    handler._process(p)
    handler._emitter.emit.assert_called_once()
    records_sent = handler._emitter.emit.call_args[0][0]
    assert len(records_sent) == 1


def test_incremental_only_sends_new_lines(data_dir, handler, state):
    p = data_dir / "projects" / "test-proj" / "sess.jsonl"
    _write_jsonl(p, [_record("u1")])
    handler._process(p)

    first_call_count = handler._emitter.emit.call_count
    _write_jsonl(p, [_record("u2")])
    handler._process(p)

    assert handler._emitter.emit.call_count == first_call_count + 1
    second_batch = handler._emitter.emit.call_args[0][0]
    assert len(second_batch) == 1
    assert second_batch[0]["uuid"] == "u2"


def test_state_not_advanced_on_emit_failure(data_dir, handler, state):
    handler._emitter.emit.return_value = False
    p = data_dir / "projects" / "test-proj" / "sess.jsonl"
    _write_jsonl(p, [_record()])

    rel = str(p.relative_to(data_dir))
    handler._process(p)

    assert state.get(rel) is None  # State not saved on failure


def test_ignores_files_outside_projects(data_dir, handler):
    p = data_dir / "other.jsonl"
    p.write_text(json.dumps(_record()) + "\n")
    handler._process(p)
    handler._emitter.emit.assert_not_called()


def test_partial_line_not_processed(data_dir, handler):
    p = data_dir / "projects" / "test-proj" / "sess.jsonl"
    # Write without trailing newline (partial flush)
    p.write_bytes(json.dumps(_record()).encode())
    handler._process(p)
    handler._emitter.emit.assert_not_called()
