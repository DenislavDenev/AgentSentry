from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from watchtower.db import get_conn
from watchtower.schema.models import ToolStat

router = APIRouter()


@router.get("/tools", response_model=list[ToolStat])
async def list_tools(
    days: int = 0,
    conn: AsyncConnection = Depends(get_conn),
) -> list[ToolStat]:
    # SQLite has no FILTER clause for aggregates — emulate via SUM(CASE WHEN ...).
    # is_error stored as INTEGER (0/1).
    # 1.0 * cast forces float division.
    rows = await conn.execute(
        text("""
            SELECT
                tool_name,
                COUNT(*)                                       AS invocation_count,
                COALESCE(SUM(result_tokens), 0)                AS result_tokens,
                SUM(CASE WHEN is_error THEN 1 ELSE 0 END)      AS error_count,
                ROUND(
                    1.0 * SUM(CASE WHEN is_error THEN 1 ELSE 0 END)
                        / NULLIF(COUNT(*), 0) * 100,
                    1
                )                                              AS error_rate_pct
            FROM tool_calls
            WHERE tool_name NOT LIKE '!_%' ESCAPE '!'
              AND (:days = 0 OR recorded_at >= (strftime('%s','now') - :days * 86400))
            GROUP BY tool_name
            ORDER BY invocation_count DESC
        """),
        {"days": days},
    )
    return [ToolStat(**dict(r._mapping)) for r in rows]
