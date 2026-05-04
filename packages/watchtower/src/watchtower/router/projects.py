from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from watchtower.db import get_conn
from watchtower.schema.models import DailyStats, ProjectDetail, ProjectSummary

router = APIRouter()


@router.get("/projects", response_model=list[ProjectSummary])
async def list_projects(
    days: int = 0,
    conn: AsyncConnection = Depends(get_conn),
) -> list[ProjectSummary]:
    rows = await conn.execute(
        text("""
            SELECT
                m.project_slug                              AS slug,
                COUNT(DISTINCT m.session_id)               AS session_count,
                COALESCE(SUM(m.input_tokens), 0)           AS input_tokens,
                COALESCE(SUM(m.output_tokens), 0)          AS output_tokens,
                COALESCE(SUM(m.cache_read_tokens), 0)      AS cache_read_tokens,
                COALESCE(SUM(m.input_tokens + m.output_tokens), 0) AS total_tokens
            FROM messages m
            WHERE :days = 0 OR m.recorded_at >= NOW() - (INTERVAL '1 day' * :days)
            GROUP BY m.project_slug
            ORDER BY total_tokens DESC
        """),
        {"days": days},
    )
    return [ProjectSummary(**dict(r._mapping)) for r in rows]


@router.get("/projects/{slug}", response_model=ProjectDetail)
async def get_project(slug: str, conn: AsyncConnection = Depends(get_conn)) -> ProjectDetail:
    row = await conn.execute(
        text("""
            SELECT
                m.project_slug                              AS slug,
                COUNT(DISTINCT m.session_id)               AS session_count,
                COALESCE(SUM(m.input_tokens), 0)           AS input_tokens,
                COALESCE(SUM(m.output_tokens), 0)          AS output_tokens,
                COALESCE(SUM(m.cache_read_tokens), 0)      AS cache_read_tokens,
                COALESCE(SUM(m.input_tokens + m.output_tokens), 0) AS total_tokens
            FROM messages m
            WHERE m.project_slug = :slug
            GROUP BY m.project_slug
        """),
        {"slug": slug},
    )
    summary = row.fetchone()
    if summary is None:
        raise HTTPException(status_code=404, detail="Project not found")

    daily_rows = await conn.execute(
        text("""
            SELECT
                DATE(recorded_at)::TEXT                    AS date,
                COALESCE(SUM(input_tokens), 0)             AS input_tokens,
                COALESCE(SUM(output_tokens), 0)            AS output_tokens,
                COALESCE(SUM(cache_read_tokens), 0)        AS cache_read_tokens,
                COALESCE(
                    SUM(cache_create_5m_tokens + cache_create_1h_tokens), 0
                )                                          AS cache_create_tokens,
                COALESCE(SUM(input_tokens + output_tokens), 0) AS total_tokens,
                COUNT(DISTINCT session_id)                 AS session_count
            FROM messages
            WHERE project_slug = :slug
            GROUP BY DATE(recorded_at)
            ORDER BY DATE(recorded_at)
        """),
        {"slug": slug},
    )
    daily = [DailyStats(**dict(r._mapping)) for r in daily_rows]
    return ProjectDetail(**dict(summary._mapping), daily=daily)
