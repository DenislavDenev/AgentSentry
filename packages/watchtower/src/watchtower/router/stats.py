from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from watchtower.db import get_conn
from watchtower.schema.models import DailyStats, OverviewStats

router = APIRouter()


@router.get("/stats/overview", response_model=OverviewStats)
async def overview(conn: AsyncConnection = Depends(get_conn)) -> OverviewStats:
    row = await conn.execute(
        text("""
            SELECT
                COUNT(DISTINCT session_id)                 AS total_sessions,
                COUNT(*)                                   AS total_messages,
                COALESCE(SUM(input_tokens), 0)             AS input_tokens,
                COALESCE(SUM(output_tokens), 0)            AS output_tokens,
                COALESCE(SUM(cache_read_tokens), 0)        AS cache_read_tokens,
                COALESCE(SUM(input_tokens + output_tokens), 0) AS total_tokens
            FROM messages
        """)
    )
    r = row.fetchone()
    data = dict(r._mapping)

    total = data["input_tokens"] + data["cache_read_tokens"]
    cache_pct = round(data["cache_read_tokens"] / total * 100, 1) if total > 0 else 0.0

    return OverviewStats(**data, cache_efficiency_pct=cache_pct)


@router.get("/stats/daily", response_model=list[DailyStats])
async def daily(
    days: int = 30,
    conn: AsyncConnection = Depends(get_conn),
) -> list[DailyStats]:
    rows = await conn.execute(
        text("""
            SELECT
                DATE(recorded_at)::TEXT                    AS date,
                COALESCE(SUM(input_tokens), 0)             AS input_tokens,
                COALESCE(SUM(output_tokens), 0)            AS output_tokens,
                COALESCE(SUM(cache_read_tokens), 0)        AS cache_read_tokens,
                COALESCE(SUM(input_tokens + output_tokens), 0) AS total_tokens,
                COUNT(DISTINCT session_id)                 AS session_count
            FROM messages
            WHERE recorded_at >= NOW() - (:days || ' days')::INTERVAL
            GROUP BY DATE(recorded_at)
            ORDER BY DATE(recorded_at)
        """),
        {"days": days},
    )
    return [DailyStats(**dict(r._mapping)) for r in rows]
