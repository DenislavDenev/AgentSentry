"""
Query endpoint tests — also require WATCHTOWER_TEST_DB.
"""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

TEST_DB = os.environ.get("WATCHTOWER_TEST_DB")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="WATCHTOWER_TEST_DB not set")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def engine():
    e = create_async_engine(TEST_DB)
    yield e
    await e.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(engine):
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE tool_calls, messages, sessions CASCADE"))
    yield


@pytest_asyncio.fixture(scope="session")
async def client(engine):
    import watchtower.db as db_module

    db_module._engine = engine

    from watchtower.__main__ import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


_BASE = {
    "session_id": "s1",
    "project_slug": "proj-a",
    "record_type": "assistant",
    "model": "claude-sonnet-4-6",
    "timestamp": "2025-06-01T10:00:00Z",
    "tool_calls": [],
}


@pytest.mark.anyio
async def test_sessions_list_empty(client):
    resp = await client.get("/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_overview_zeros_on_empty_db(client):
    resp = await client.get("/stats/overview")
    assert resp.status_code == 200
    d = resp.json()
    assert d["total_sessions"] == 0
    assert d["total_tokens"] == 0


@pytest.mark.anyio
async def test_projects_after_ingest(client):
    await client.post(
        "/ingest",
        json={
            "records": [
                {**_BASE, "uuid": "u1", "message_id": "m1",
                 "input_tokens": 300, "output_tokens": 100},
                {**_BASE, "uuid": "u2", "message_id": "m2",
                 "input_tokens": 200, "output_tokens": 80},
            ]
        },
    )
    resp = await client.get("/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) == 1
    assert projects[0]["slug"] == "proj-a"
    assert projects[0]["input_tokens"] == 500


@pytest.mark.anyio
async def test_project_404(client):
    resp = await client.get("/projects/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_models_endpoint(client):
    await client.post(
        "/ingest",
        json={"records": [
            {**_BASE, "uuid": "u3", "message_id": "m3",
             "input_tokens": 50, "output_tokens": 25},
        ]},
    )
    resp = await client.get("/models")
    assert resp.status_code == 200
