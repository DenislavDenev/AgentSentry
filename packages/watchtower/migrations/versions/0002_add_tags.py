"""Add tags column to messages

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-10 00:00:00.000000

Stores a JSON array of source tags (e.g. '["codex"]') so the prompts
endpoint can filter by invocation source.  Defaults to '[]' for all
existing rows.
"""

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op

    op.execute(
        "ALTER TABLE messages ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'"
    )


def downgrade() -> None:
    # SQLite does not support DROP COLUMN before 3.35. Use render_as_batch
    # in env.py (already configured) to handle this via table rebuild if needed.
    from alembic import op

    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_column("tags")
