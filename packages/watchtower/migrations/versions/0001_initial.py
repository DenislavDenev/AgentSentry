"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op

    op.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id           TEXT PRIMARY KEY,
            project_slug TEXT NOT NULL,
            started_at   TIMESTAMPTZ,
            ended_at     TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            uuid                    TEXT PRIMARY KEY,
            message_id              TEXT,
            session_id              TEXT NOT NULL REFERENCES sessions(id),
            project_slug            TEXT NOT NULL,
            record_type             TEXT,
            model                   TEXT,
            input_tokens            INTEGER NOT NULL DEFAULT 0,
            output_tokens           INTEGER NOT NULL DEFAULT 0,
            cache_read_tokens       INTEGER NOT NULL DEFAULT 0,
            cache_create_5m_tokens  INTEGER NOT NULL DEFAULT 0,
            cache_create_1h_tokens  INTEGER NOT NULL DEFAULT 0,
            prompt_text             TEXT,
            prompt_chars            INTEGER,
            is_sidechain            BOOLEAN NOT NULL DEFAULT FALSE,
            agent_id                TEXT,
            recorded_at             TIMESTAMPTZ NOT NULL,
            UNIQUE (session_id, message_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS tool_calls (
            id            BIGSERIAL PRIMARY KEY,
            message_uuid  TEXT NOT NULL REFERENCES messages(uuid) ON DELETE CASCADE,
            session_id    TEXT NOT NULL,
            tool_name     TEXT NOT NULL,
            target        TEXT,
            result_tokens INTEGER NOT NULL DEFAULT 0,
            is_error      BOOLEAN NOT NULL DEFAULT FALSE,
            recorded_at   TIMESTAMPTZ NOT NULL
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_session  ON messages(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_project  ON messages(project_slug)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_recorded ON messages(recorded_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_name   ON tool_calls(tool_name)")


def downgrade() -> None:
    from alembic import op

    op.execute("DROP TABLE IF EXISTS tool_calls")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS sessions")
