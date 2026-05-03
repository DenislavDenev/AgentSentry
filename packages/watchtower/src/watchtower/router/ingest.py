from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from watchtower.db import get_conn
from watchtower.schema.models import IngestRequest

router = APIRouter()


@router.post("/ingest", status_code=201)
async def ingest(body: IngestRequest, conn: AsyncConnection = Depends(get_conn)) -> dict:
    async with conn.begin():
        for rec in body.records:
            # Upsert session (min/max timestamps)
            await conn.execute(
                text("""
                    INSERT INTO sessions (id, project_slug, started_at, ended_at)
                    VALUES (:id, :slug, :ts, :ts)
                    ON CONFLICT (id) DO UPDATE SET
                        started_at = LEAST(sessions.started_at, EXCLUDED.started_at),
                        ended_at   = GREATEST(sessions.ended_at, EXCLUDED.ended_at)
                """),
                {"id": rec.session_id, "slug": rec.project_slug, "ts": rec.timestamp},
            )

            # Skip records without message_id that would violate the unique constraint
            # user records (tool results, prompts) have no message_id — insert normally
            if rec.message_id is not None:
                result = await conn.execute(
                    text("""
                        INSERT INTO messages (
                            uuid, message_id, session_id, project_slug, record_type, model,
                            input_tokens, output_tokens, cache_read_tokens,
                            cache_create_5m_tokens, cache_create_1h_tokens,
                            prompt_text, prompt_chars, is_sidechain, agent_id, recorded_at
                        ) VALUES (
                            :uuid, :mid, :sid, :slug, :rtype, :model,
                            :in_tok, :out_tok, :cr_tok, :cc5_tok, :cc1_tok,
                            :ptxt, :pchars, :sidechain, :agent_id, :recorded_at
                        )
                        ON CONFLICT (session_id, message_id) DO UPDATE SET
                            uuid                  = EXCLUDED.uuid,
                            input_tokens          = EXCLUDED.input_tokens,
                            output_tokens         = EXCLUDED.output_tokens,
                            cache_read_tokens     = EXCLUDED.cache_read_tokens,
                            cache_create_5m_tokens = EXCLUDED.cache_create_5m_tokens,
                            cache_create_1h_tokens = EXCLUDED.cache_create_1h_tokens,
                            model                 = EXCLUDED.model,
                            recorded_at           = EXCLUDED.recorded_at
                        RETURNING uuid
                    """),
                    _msg_params(rec),
                )
                row = result.fetchone()
                if row is None:
                    continue
                msg_uuid = row[0]
            else:
                await conn.execute(
                    text("""
                        INSERT INTO messages (
                            uuid, message_id, session_id, project_slug, record_type, model,
                            input_tokens, output_tokens, cache_read_tokens,
                            cache_create_5m_tokens, cache_create_1h_tokens,
                            prompt_text, prompt_chars, is_sidechain, agent_id, recorded_at
                        ) VALUES (
                            :uuid, :mid, :sid, :slug, :rtype, :model,
                            :in_tok, :out_tok, :cr_tok, :cc5_tok, :cc1_tok,
                            :ptxt, :pchars, :sidechain, :agent_id, :recorded_at
                        )
                        ON CONFLICT DO NOTHING
                    """),
                    _msg_params(rec),
                )
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
                        "err": tc.is_error,
                        "recorded_at": rec.timestamp,
                    },
                )

    return {"inserted": len(body.records)}


def _msg_params(rec) -> dict:
    return {
        "uuid": rec.uuid,
        "mid": rec.message_id,
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
        "sidechain": rec.is_sidechain,
        "agent_id": rec.agent_id,
        "recorded_at": rec.timestamp,
    }
