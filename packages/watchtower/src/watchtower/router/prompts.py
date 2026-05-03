from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from watchtower.db import get_conn
from watchtower.schema.models import PromptStat

router = APIRouter()


@router.get("/prompts", response_model=list[PromptStat])
async def list_prompts(
    limit: int = 50,
    conn: AsyncConnection = Depends(get_conn),
) -> list[PromptStat]:
    rows = await conn.execute(
        text("""
            SELECT uuid, session_id, project_slug,
                   prompt_text, prompt_chars,
                   COALESCE(input_tokens, 0) AS input_tokens,
                   recorded_at::TEXT AS recorded_at
            FROM messages
            WHERE record_type = 'user'
              AND prompt_text IS NOT NULL
              AND prompt_chars IS NOT NULL
            ORDER BY input_tokens DESC, prompt_chars DESC
            LIMIT :limit
        """),
        {"limit": limit},
    )
    return [PromptStat(**dict(r._mapping)) for r in rows]
