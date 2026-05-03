from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from watchtower.db import get_conn

router = APIRouter()


class PromptStat(BaseModel):
    uuid: str
    session_id: str
    project_slug: str
    prompt_text: str
    prompt_chars: int
    recorded_at: str


@router.get("/prompts", response_model=list[PromptStat])
async def list_prompts(
    limit: int = 50,
    conn: AsyncConnection = Depends(get_conn),
) -> list[PromptStat]:
    rows = await conn.execute(
        text("""
            SELECT uuid, session_id, project_slug,
                   prompt_text, prompt_chars,
                   recorded_at::TEXT AS recorded_at
            FROM messages
            WHERE record_type = 'user'
              AND prompt_text IS NOT NULL
              AND prompt_chars IS NOT NULL
            ORDER BY prompt_chars DESC
            LIMIT :limit
        """),
        {"limit": limit},
    )
    return [PromptStat(**dict(r._mapping)) for r in rows]
