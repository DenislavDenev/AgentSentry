"""Query endpoint tests against a real SQLite database."""

import pytest

_BASE = {
    "session_id": "s1",
    "project_slug": "proj-a",
    "record_type": "assistant",
    "model": "claude-sonnet-4-6",
    "timestamp": "2025-06-01T10:00:00Z",
    "tool_calls": [],
}


@pytest.mark.asyncio
async def test_sessions_list_empty(client):
    resp = await client.get("/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_overview_zeros_on_empty_db(client):
    resp = await client.get("/stats/overview")
    assert resp.status_code == 200
    d = resp.json()
    assert d["total_sessions"] == 0
    assert d["total_tokens"] == 0


@pytest.mark.asyncio
async def test_projects_after_ingest(client):
    await client.post(
        "/ingest",
        json={
            "records": [
                {
                    **_BASE,
                    "uuid": "u1",
                    "message_id": "m1",
                    "input_tokens": 300,
                    "output_tokens": 100,
                },
                {
                    **_BASE,
                    "uuid": "u2",
                    "message_id": "m2",
                    "input_tokens": 200,
                    "output_tokens": 80,
                },
            ]
        },
    )
    resp = await client.get("/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) == 1
    assert projects[0]["slug"] == "proj-a"
    assert projects[0]["input_tokens"] == 500


@pytest.mark.asyncio
async def test_project_404(client):
    resp = await client.get("/projects/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_models_endpoint(client):
    await client.post(
        "/ingest",
        json={
            "records": [
                {
                    **_BASE,
                    "uuid": "u3",
                    "message_id": "m3",
                    "input_tokens": 50,
                    "output_tokens": 25,
                },
            ]
        },
    )
    resp = await client.get("/models")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_daily_endpoint_groups_by_date(client):
    """Verify the date(col, 'unixepoch') GROUP BY emits 'YYYY-MM-DD' keys."""
    await client.post(
        "/ingest",
        json={
            "records": [
                {**_BASE, "uuid": "d1", "message_id": "dm1", "timestamp": "2025-06-01T01:00:00Z",
                 "input_tokens": 100, "output_tokens": 0},
                {**_BASE, "uuid": "d2", "message_id": "dm2", "timestamp": "2025-06-01T23:00:00Z",
                 "input_tokens": 200, "output_tokens": 0},
                {**_BASE, "uuid": "d3", "message_id": "dm3", "timestamp": "2025-06-02T01:00:00Z",
                 "input_tokens": 50, "output_tokens": 0},
            ]
        },
    )
    resp = await client.get("/stats/daily?days=0")
    assert resp.status_code == 200
    rows = {r["date"]: r for r in resp.json()}
    assert rows["2025-06-01"]["input_tokens"] == 300
    assert rows["2025-06-02"]["input_tokens"] == 50


@pytest.mark.asyncio
async def test_session_duration_computed_from_epoch(client):
    """Session started_at/ended_at are integer epoch; duration is direct subtraction."""
    await client.post(
        "/ingest",
        json={
            "records": [
                {**_BASE, "uuid": "x1", "message_id": "xm1",
                 "timestamp": "2025-06-01T10:00:00Z"},
                {**_BASE, "uuid": "x2", "message_id": "xm2",
                 "timestamp": "2025-06-01T10:05:00Z"},
            ]
        },
    )
    resp = await client.get("/sessions/s1")
    assert resp.status_code == 200
    d = resp.json()
    assert d["duration_secs"] == 300


@pytest.mark.asyncio
async def test_prompt_attribution_via_parent_uuid(client):
    """User prompts rank by the assistant response that has parent_uuid = prompt.uuid."""
    await client.post(
        "/ingest",
        json={
            "records": [
                # User prompt
                {
                    "uuid": "user-1", "session_id": "s1", "project_slug": "proj-a",
                    "record_type": "user", "model": None, "timestamp": "2025-06-01T10:00:00Z",
                    "prompt_text": "hello world", "prompt_chars": 11,
                    "tool_calls": [],
                },
                # Assistant response with parent_uuid pointing at the user prompt
                {
                    **_BASE,
                    "uuid": "asst-1", "message_id": "m-asst-1",
                    "parent_uuid": "user-1",
                    "input_tokens": 1000, "output_tokens": 500,
                    "cache_create_5m_tokens": 200,
                },
            ]
        },
    )
    resp = await client.get("/prompts?limit=5")
    assert resp.status_code == 200
    prompts = resp.json()
    assert len(prompts) == 1
    p = prompts[0]
    assert p["uuid"] == "user-1"
    assert p["billable_tokens"] == 1700  # 1000 + 500 + 200
    assert p["recorded_at"] == "2025-06-01T10:00:00Z"  # ISO format
