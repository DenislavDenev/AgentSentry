"""Integration tests for POST /ingest against a real SQLite database."""

import pytest

_SAMPLE_RECORD = {
    "uuid": "u1",
    "message_id": "m1",
    "session_id": "sess-1",
    "project_slug": "test-project",
    "record_type": "assistant",
    "model": "claude-sonnet-4-6",
    "timestamp": "2025-01-01T00:00:00Z",
    "input_tokens": 100,
    "output_tokens": 50,
    "cache_read_tokens": 10,
    "cache_create_5m_tokens": 0,
    "cache_create_1h_tokens": 0,
    "tool_calls": [{"name": "Read", "target": "/foo.py", "result_tokens": 25, "is_error": False}],
}


@pytest.mark.asyncio
async def test_ingest_returns_201(client):
    resp = await client.post("/ingest", json={"records": [_SAMPLE_RECORD]})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_ingest_idempotent_on_message_id(client):
    rec2 = {**_SAMPLE_RECORD, "uuid": "u2", "input_tokens": 200}
    await client.post("/ingest", json={"records": [_SAMPLE_RECORD]})
    await client.post("/ingest", json={"records": [rec2]})

    resp = await client.get("/sessions/sess-1")
    assert resp.status_code == 200
    data = resp.json()
    # Dedup: only one message row, with the latest token count
    assert data["message_count"] == 1
    assert data["input_tokens"] == 200


@pytest.mark.asyncio
async def test_tool_calls_stored(client):
    await client.post("/ingest", json={"records": [_SAMPLE_RECORD]})
    resp = await client.get("/tools")
    assert resp.status_code == 200
    tools = {t["tool_name"]: t for t in resp.json()}
    assert "Read" in tools
    assert tools["Read"]["invocation_count"] == 1
