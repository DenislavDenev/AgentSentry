from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from watchtower.db import get_conn
from watchtower.schema.models import ToolStat

router = APIRouter()


@router.get("/tools", response_model=list[ToolStat])
async def list_tools(conn: AsyncConnection = Depends(get_conn)) -> list[ToolStat]:
    rows = await conn.execute(
        text("""
            SELECT
                tool_name,
                COUNT(*)                                AS invocation_count,
                COALESCE(SUM(result_tokens), 0)        AS result_tokens,
                COUNT(*) FILTER (WHERE is_error)       AS error_count,
                ROUND(
                    COUNT(*) FILTER (WHERE is_error)::NUMERIC / NULLIF(COUNT(*), 0) * 100,
                    1
                )                                      AS error_rate_pct
            FROM tool_calls
            GROUP BY tool_name
            ORDER BY invocation_count DESC
        """)
    )
    return [ToolStat(**dict(r._mapping)) for r in rows]
