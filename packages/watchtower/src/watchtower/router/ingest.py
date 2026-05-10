import json
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from watchtower.db import get_engine
from watchtower.schema.models import IngestRequest, RecordIn

router = APIRouter()


def _epoch(dt: datetime) -> int:
    """Convert a datetime to integer Unix-epoch seconds (UTC).

    Naïve datetimes are treated as UTC — Beacon adapters always parse Claude
    Code timestamps with explicit Zulu suffix, so this is consistent with what
    the parser emits. Future adapters MUST emit timezone-aware datetimes.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


async def ingest_records(records: list[RecordIn]) -> None:
    """Core ingest logic — callable from both the HTTP route and the scout thread.

    Opens its own connection from the shared engine so callers (e.g. the
    watchdog thread via run_coroutine_threadsafe) don't need to hold a
    connection across thread boundaries.
    """
    async with get_engine().connect() as conn:
        async with conn.begin():
            for rec in records:
                await _insert_record(rec, conn)


@router.post("/ingest", status_code=201)
async def ingest(body: IngestRequest) -> dict:
    await ingest_records(body.records)
    return {"inserted": len(body.records)}


async def _insert_record(rec: RecordIn, conn: AsyncConnection) -> None:
    ts = _epoch(rec.timestamp)

    # Upsert session (min/max timestamps). SQLite's scalar MIN/MAX
    # return NULL if any arg is NULL — Postgres's LEAST/GREATEST
    # ignored NULLs. The IFNULL pair makes us NULL-safe: if the
    # stored bound is NULL, fall back to EXCLUDED, and vice versa.
    await conn.execute(
        text("""
            INSERT INTO sessions (id, project_slug, started_at, ended_at)
            VALUES (:id, :slug, :ts, :ts)
            ON CONFLICT (id) DO UPDATE SET
                started_at = MIN(
                    IFNULL(sessions.started_at, EXCLUDED.started_at),
                    IFNULL(EXCLUDED.started_at, sessions.started_at)
                ),
                ended_at   = MAX(
                    IFNULL(sessions.ended_at, EXCLUDED.ended_at),
                    IFNULL(EXCLUDED.ended_at, sessions.ended_at)
                )
        """),
        {"id": rec.session_id, "slug": rec.project_slug, "ts": ts},
    )

    # Skip records without message_id that would violate the unique
    # constraint. user records (tool results, prompts) have no
    # message_id — insert normally.
    if rec.message_id is not None:
        # Remove any stale row with the same (session_id, message_id)
        # but a different uuid — handles streaming snapshots that
        # arrived in a previous batch under an older uuid. SQLite
        # serialises writers via the file lock, so the Postgres
        # advisory-lock dance is not needed here.
        await conn.execute(
            text("""
                DELETE FROM messages
                WHERE session_id = :sid
                  AND message_id = :mid
                  AND uuid      != :uuid
            """),
            {"sid": rec.session_id, "mid": rec.message_id, "uuid": rec.uuid},
        )
        # Upsert on uuid (PK). If this exact record was already
        # ingested (same uuid) we refresh the token fields in case a
        # later snapshot of the same message was re-delivered.
        result = await conn.execute(
            text("""
                INSERT INTO messages (
                    uuid, message_id, parent_uuid,
                    session_id, project_slug, record_type, model,
                    input_tokens, output_tokens, cache_read_tokens,
                    cache_create_5m_tokens, cache_create_1h_tokens,
                    prompt_text, prompt_chars, is_sidechain, agent_id, recorded_at, tags
                ) VALUES (
                    :uuid, :mid, :puuid,
                    :sid, :slug, :rtype, :model,
                    :in_tok, :out_tok, :cr_tok, :cc5_tok, :cc1_tok,
                    :ptxt, :pchars, :sidechain, :agent_id, :recorded_at, :tags
                )
                ON CONFLICT (uuid) DO UPDATE SET
                    input_tokens           = EXCLUDED.input_tokens,
                    output_tokens          = EXCLUDED.output_tokens,
                    cache_read_tokens      = EXCLUDED.cache_read_tokens,
                    cache_create_5m_tokens = EXCLUDED.cache_create_5m_tokens,
                    cache_create_1h_tokens = EXCLUDED.cache_create_1h_tokens,
                    parent_uuid            = EXCLUDED.parent_uuid,
                    model                  = EXCLUDED.model,
                    recorded_at            = EXCLUDED.recorded_at,
                    tags                   = EXCLUDED.tags
                RETURNING uuid
            """),
            _msg_params(rec, ts),
        )
        row = result.fetchone()
        if row is None:
            return
        msg_uuid = row[0]
        # Remove stale tool_calls before re-inserting — the pre-DELETE
        # above handles the different-uuid case via ON DELETE CASCADE,
        # but the DO UPDATE path leaves the old rows alive.
        if rec.tool_calls:
            await conn.execute(
                text("DELETE FROM tool_calls WHERE message_uuid = :uuid"),
                {"uuid": msg_uuid},
            )
    else:
        result = await conn.execute(
            text("""
                INSERT INTO messages (
                    uuid, message_id, parent_uuid,
                    session_id, project_slug, record_type, model,
                    input_tokens, output_tokens, cache_read_tokens,
                    cache_create_5m_tokens, cache_create_1h_tokens,
                    prompt_text, prompt_chars, is_sidechain, agent_id, recorded_at, tags
                ) VALUES (
                    :uuid, :mid, :puuid,
                    :sid, :slug, :rtype, :model,
                    :in_tok, :out_tok, :cr_tok, :cc5_tok, :cc1_tok,
                    :ptxt, :pchars, :sidechain, :agent_id, :recorded_at, :tags
                )
                ON CONFLICT (uuid) DO NOTHING
                RETURNING uuid
            """),
            _msg_params(rec, ts),
        )
        row = result.fetchone()
        # If the user record already existed (DO NOTHING fired), skip
        # its tool_calls too — they were inserted on the original.
        if row is None:
            return
        msg_uuid = rec.uuid

    for tc in rec.tool_calls:
        await conn.execute(
            text("""
                INSERT INTO tool_calls
                    (message_uuid, session_id, tool_name, target,
                     result_tokens, is_error, recorded_at)
                VALUES
                    (:msg_uuid, :sid, :name, :target, :rtok, :err, :recorded_at)
            """),
            {
                "msg_uuid": msg_uuid,
                "sid": rec.session_id,
                "name": tc.name,
                "target": tc.target,
                "rtok": tc.result_tokens,
                "err": 1 if tc.is_error else 0,
                "recorded_at": ts,
            },
        )


def _msg_params(rec: RecordIn, ts: int) -> dict:
    return {
        "uuid": rec.uuid,
        "mid": rec.message_id,
        "puuid": rec.parent_uuid,
        "sid": rec.session_id,
        "slug": rec.project_slug,
        "rtype": rec.record_type,
        "model": rec.model,
        "in_tok": rec.input_tokens,
        "out_tok": rec.output_tokens,
        "cr_tok": rec.cache_read_tokens,
        "cc5_tok": rec.cache_create_5m_tokens,
        "cc1_tok": rec.cache_create_1h_tokens,
        "ptxt": rec.prompt_text,
        "pchars": rec.prompt_chars,
        "sidechain": 1 if rec.is_sidechain else 0,
        "agent_id": rec.agent_id,
        "recorded_at": ts,
        "tags": json.dumps(rec.tags),
    }
