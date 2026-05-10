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
    resp = await client.get("/api/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_overview_zeros_on_empty_db(client):
    resp = await client.get("/api/stats/overview")
    assert resp.status_code == 200
    d = resp.json()
    assert d["total_sessions"] == 0
    assert d["total_tokens"] == 0


@pytest.mark.asyncio
async def test_projects_after_ingest(client):
    await client.post(
        "/api/ingest",
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
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) == 1
    assert projects[0]["slug"] == "proj-a"
    assert projects[0]["input_tokens"] == 500


@pytest.mark.asyncio
async def test_project_404(client):
    resp = await client.get("/api/projects/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_models_endpoint(client):
    await client.post(
        "/api/ingest",
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
    resp = await client.get("/api/models")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_daily_endpoint_groups_by_date(client):
    """Verify the date(col, 'unixepoch') GROUP BY emits 'YYYY-MM-DD' keys."""
    await client.post(
        "/api/ingest",
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
    resp = await client.get("/api/stats/daily?days=0")
    assert resp.status_code == 200
    rows = {r["date"]: r for r in resp.json()}
    assert rows["2025-06-01"]["input_tokens"] == 300
    assert rows["2025-06-02"]["input_tokens"] == 50


@pytest.mark.asyncio
async def test_session_duration_computed_from_epoch(client):
    """Session started_at/ended_at are integer epoch; duration is direct subtraction."""
    await client.post(
        "/api/ingest",
        json={
            "records": [
                {**_BASE, "uuid": "x1", "message_id": "xm1",
                 "timestamp": "2025-06-01T10:00:00Z"},
                {**_BASE, "uuid": "x2", "message_id": "xm2",
                 "timestamp": "2025-06-01T10:05:00Z"},
            ]
        },
    )
    resp = await client.get("/api/sessions/s1")
    assert resp.status_code == 200
    d = resp.json()
    assert d["duration_secs"] == 300


@pytest.mark.asyncio
async def test_prompt_attribution_via_parent_uuid(client):
    """User prompts rank by the assistant response that has parent_uuid = prompt.uuid."""
    await client.post(
        "/api/ingest",
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
    resp = await client.get("/api/prompts?limit=5")
    assert resp.status_code == 200
    prompts = resp.json()
    assert len(prompts) == 1
    p = prompts[0]
    assert p["uuid"] == "user-1"
    assert p["billable_tokens"] == 1700  # 1000 + 500 + 200
    assert p["recorded_at"] == "2025-06-01T10:00:00Z"  # ISO format


@pytest.mark.asyncio
async def test_session_upsert_null_safe(client, engine):
    """Reproduce the SQLite scalar MIN/MAX NULL trap.

    A session row with started_at=NULL must not propagate the NULL when a new
    record arrives — the IFNULL pair in the upsert should heal it.
    """
    from sqlalchemy import text

    # Pre-seed a session with a NULL bound (simulates a partial migration).
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO sessions (id, project_slug, started_at, ended_at) "
                 "VALUES ('null-sess', 'proj-a', NULL, NULL)")
        )

    # Now ingest a record into that session.
    await client.post(
        "/api/ingest",
        json={
            "records": [
                {**_BASE,
                 "uuid": "n1", "message_id": "nm1",
                 "session_id": "null-sess",
                 "timestamp": "2025-06-01T10:00:00Z"},
            ]
        },
    )

    resp = await client.get("/api/sessions/null-sess")
    assert resp.status_code == 200
    d = resp.json()
    # Both bounds should now be the ingested timestamp, not NULL.
    assert d["started_at"] is not None
    assert d["ended_at"] is not None
    assert d["duration_secs"] == 0


def test_migrate_pg_to_sqlite_bool_normalizer():
    """Strict boolean normaliser must reject ambiguous psycopg shapes."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    try:
        from migrate_pg_to_sqlite import _b
    finally:
        sys.path.pop(0)

    assert _b(True) == 1
    assert _b(False) == 0
    assert _b(None) == 0
    assert _b(1) == 1
    assert _b(0) == 0
    assert _b("t") == 1
    assert _b("f") == 0
    assert _b("true") == 1
    assert _b("FALSE") == 0
    assert _b(b"t") == 1
    assert _b(b"f") == 0
    assert _b(b"\x00") == 0
    assert _b(b"\x01") == 1

    # Unknown shapes must raise — the bug we're guarding against was silent
    # truth-coercion of weird bytes.
    import pytest
    with pytest.raises(ValueError):
        _b("maybe")
    with pytest.raises(ValueError):
        _b(b"maybe")
    with pytest.raises(ValueError):
        _b(3.14)
