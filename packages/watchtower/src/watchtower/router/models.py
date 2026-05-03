from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from watchtower.db import get_conn
from watchtower.schema.models import ModelStat

router = APIRouter()


@router.get("/models", response_model=list[ModelStat])
async def list_models(conn: AsyncConnection = Depends(get_conn)) -> list[ModelStat]:
    rows = await conn.execute(
        text("""
            SELECT
                COALESCE(model, 'unknown')                 AS model,
                COALESCE(SUM(input_tokens), 0)             AS input_tokens,
                COALESCE(SUM(output_tokens), 0)            AS output_tokens,
                COALESCE(SUM(input_tokens + output_tokens), 0) AS total_tokens,
                COUNT(*)                                   AS message_count
            FROM messages
            WHERE record_type = 'assistant'
              AND model IS NOT NULL
              AND model != '<synthetic>'
              AND model NOT IN ('synthetic', 'unknown')
            GROUP BY model
            ORDER BY total_tokens DESC
        """)
    )
    return [ModelStat(**dict(r._mapping)) for r in rows]
