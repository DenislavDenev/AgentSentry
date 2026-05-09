"""Initial SQLite schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00.000000

Schema notes:
- Timestamps are INTEGER Unix-epoch seconds (UTC). Avoids the float-day drift of
  julianday() and the ISO-8601 parsing ambiguity of TEXT timestamps. Boundary
  cases (NULL, sub-second precision, midnight UTC) are covered by parity tests.
- BOOLEANs are stored as INTEGER (SQLite has no native BOOLEAN). 0/1 round-trip
  through SQLAlchemy's Boolean type.
- BIGSERIAL becomes INTEGER PRIMARY KEY AUTOINCREMENT.
- All Postgres-specific syntax has been removed.
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
            started_at   INTEGER,
            ended_at     INTEGER
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            uuid                    TEXT PRIMARY KEY,
            message_id              TEXT,
            parent_uuid             TEXT,
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
            is_sidechain            INTEGER NOT NULL DEFAULT 0,
            agent_id                TEXT,
            recorded_at             INTEGER NOT NULL,
            UNIQUE (session_id, message_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS tool_calls (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            message_uuid  TEXT NOT NULL REFERENCES messages(uuid) ON DELETE CASCADE,
            session_id    TEXT NOT NULL,
            tool_name     TEXT NOT NULL,
            target        TEXT,
            result_tokens INTEGER NOT NULL DEFAULT 0,
            is_error      INTEGER NOT NULL DEFAULT 0,
            recorded_at   INTEGER NOT NULL
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_session     ON messages(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_project     ON messages(project_slug)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_recorded    ON messages(recorded_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_parent_uuid ON messages(parent_uuid)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_session   ON tool_calls(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_name      ON tool_calls(tool_name)")


def downgrade() -> None:
    from alembic import op

    op.execute("DROP TABLE IF EXISTS tool_calls")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS sessions")
