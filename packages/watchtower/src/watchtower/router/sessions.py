from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from watchtower.db import get_conn
from watchtower.schema.models import MessageOut, SessionDetail, SessionSummary

router = APIRouter()


# Common SELECT clause for the aggregated session-summary shape.
# Timestamps are INTEGER epoch seconds; duration is just a subtraction.
# Pydantic v2 accepts int for `datetime` fields (epoch seconds), so the
# response model's API contract is unchanged.
_SUMMARY_COLS = """
    s.id,
    s.project_slug,
    s.started_at,
    s.ended_at,
    (s.ended_at - s.started_at)                            AS duration_secs,
    COALESCE(SUM(m.input_tokens), 0)                       AS input_tokens,
    COALESCE(SUM(m.output_tokens), 0)                      AS output_tokens,
    COALESCE(SUM(m.cache_read_tokens), 0)                  AS cache_read_tokens,
    COALESCE(SUM(m.input_tokens + m.output_tokens), 0)     AS total_tokens,
    COUNT(m.uuid)                                          AS message_count
"""


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    days: int = 0,
    conn: AsyncConnection = Depends(get_conn),
) -> list[SessionSummary]:
    rows = await conn.execute(
        text(f"""
            SELECT {_SUMMARY_COLS}
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            WHERE :days = 0 OR s.started_at >= (strftime('%s','now') - :days * 86400)
            GROUP BY s.id
            ORDER BY s.started_at DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """),
        {"limit": limit, "offset": offset, "days": days},
    )
    return [SessionSummary(**dict(r._mapping)) for r in rows]


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    conn: AsyncConnection = Depends(get_conn),
) -> SessionDetail:
    row = await conn.execute(
        text(f"""
            SELECT {_SUMMARY_COLS}
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            WHERE s.id = :sid
            GROUP BY s.id
        """),
        {"sid": session_id},
    )
    summary = row.fetchone()
    if summary is None:
        raise HTTPException(status_code=404, detail="Session not found")

    msgs = await conn.execute(
        text("""
            SELECT uuid, message_id, parent_uuid, record_type, model,
                   input_tokens, output_tokens, cache_read_tokens,
                   cache_create_5m_tokens, cache_create_1h_tokens,
                   prompt_text, prompt_chars, is_sidechain, agent_id, recorded_at
            FROM messages
            WHERE session_id = :sid
            ORDER BY recorded_at
        """),
        {"sid": session_id},
    )
    messages = [MessageOut(**dict(r._mapping)) for r in msgs]
    return SessionDetail(**dict(summary._mapping), messages=messages)
