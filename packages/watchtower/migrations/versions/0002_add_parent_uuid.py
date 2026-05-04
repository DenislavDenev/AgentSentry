"""Add parent_uuid to messages

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-01 00:00:00.000000
"""

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op

    # Nullable — existing rows default to NULL; new records are populated by the parser.
    op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS parent_uuid TEXT")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_parent_uuid ON messages(parent_uuid)")


def downgrade() -> None:
    from alembic import op

    op.execute("DROP INDEX IF EXISTS idx_messages_parent_uuid")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS parent_uuid")
