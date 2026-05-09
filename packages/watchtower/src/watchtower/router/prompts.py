from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from watchtower.db import get_conn
from watchtower.schema.models import PromptStat

router = APIRouter()


@router.get("/prompts", response_model=list[PromptStat])
async def list_prompts(
    limit: int = 50,
    days: int = 0,
    conn: AsyncConnection = Depends(get_conn),
) -> list[PromptStat]:
    # Join each user prompt to the assistant response that has parent_uuid = prompt.uuid.
    # Rank by billable_tokens (assistant input + output + cache creation) so the most
    # expensive prompts appear first. User-row input_tokens are always 0 and useless for
    # ranking. Falls back to prompt_chars when no assistant response is linked yet.
    #
    # recorded_at is INTEGER epoch — emit as ISO-8601 Z for the API contract.
    rows = await conn.execute(
        text("""
            SELECT
                u.uuid,
                u.session_id,
                u.project_slug,
                u.prompt_text,
                u.prompt_chars,
                strftime('%Y-%m-%dT%H:%M:%SZ', u.recorded_at, 'unixepoch') AS recorded_at,
                COALESCE(a.input_tokens, 0)                                AS input_tokens,
                COALESCE(a.output_tokens, 0)                               AS output_tokens,
                COALESCE(
                    a.cache_create_5m_tokens + a.cache_create_1h_tokens, 0
                )                                                          AS cache_create_tokens,
                COALESCE(
                    a.input_tokens + a.output_tokens
                    + a.cache_create_5m_tokens + a.cache_create_1h_tokens,
                    0
                )                                                          AS billable_tokens
            FROM messages u
            LEFT JOIN messages a
                   ON a.parent_uuid  = u.uuid
                  AND a.record_type  = 'assistant'
            WHERE u.record_type   = 'user'
              AND u.prompt_text   IS NOT NULL
              AND (:days = 0 OR u.recorded_at >= (strftime('%s','now') - :days * 86400))
            ORDER BY billable_tokens DESC, u.prompt_chars DESC
            LIMIT :limit
        """),
        {"limit": limit, "days": days},
    )
    return [PromptStat(**dict(r._mapping)) for r in rows]
