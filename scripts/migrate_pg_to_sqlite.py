#!/usr/bin/env python3
"""One-shot Postgres -> SQLite migration.

Reads the current production Postgres database, converts TIMESTAMPTZ values to
integer Unix-epoch seconds, and writes a fresh SQLite file with schema 0001
already applied (via Alembic).

Usage on CT 111:
    PG_URL=postgresql://agentsentry:PASS@localhost:5432/agentsentry \\
    SQLITE_PATH=/var/lib/agentsentry/agentsentry.db \\
    /root/.local/bin/uv run python scripts/migrate_pg_to_sqlite.py

Idempotent: refuses to overwrite an existing SQLite file. Delete it manually
to re-run.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# psycopg is only needed at runtime — import lazily inside main() so the
# tests can import _b/_s/_epoch without pulling in a Postgres driver.


def _epoch(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _s(v):
    """Decode psycopg's bytes outputs to str for SQLite TEXT columns.

    Some psycopg adapter / connection configurations return TEXT columns as
    bytes. SQLite would store those as BLOBs, breaking every text comparison
    in the query layer. Force str everywhere.
    """
    if v is None:
        return None
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return v


def _b(v) -> int:
    """Strict normaliser for psycopg boolean values.

    Postgres BOOLEAN through psycopg is normally Python bool, but binary mode
    or non-default adapters can deliver ints, strings, or bytes. A naive
    `1 if v else 0` is wrong for `b'\\x00'`, `b'f'`, and `'f'` — all three
    are Python-truthy and would migrate as 1. Raises on shapes we haven't
    seen so unknown adapter behaviour fails loudly instead of silently
    inflating sidechain/error flags.
    """
    if v is None:
        return 0
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, int):
        return 1 if v != 0 else 0
    if isinstance(v, (bytes, str)):
        s = v.decode("utf-8", errors="replace") if isinstance(v, bytes) else v
        s = s.strip().lower()
        if s in ("t", "true", "1", "y", "yes"):
            return 1
        if s in ("f", "false", "0", "n", "no", ""):
            return 0
        # Single byte: handle b'\x00' / b'\x01' shapes.
        if isinstance(v, bytes) and len(v) == 1:
            return 1 if v != b"\x00" else 0
    raise ValueError(f"Cannot normalise boolean value {v!r} ({type(v).__name__})")


def main() -> int:
    import psycopg
    from sqlalchemy import create_engine, text

    pg_url = os.environ.get("PG_URL")
    sqlite_path = os.environ.get("SQLITE_PATH")
    if not pg_url or not sqlite_path:
        print("ERROR: set PG_URL and SQLITE_PATH env vars", file=sys.stderr)
        return 2

    sqlite_file = Path(sqlite_path)
    if sqlite_file.exists():
        print(f"ERROR: {sqlite_file} already exists; refusing to overwrite", file=sys.stderr)
        return 2

    sqlite_file.parent.mkdir(parents=True, exist_ok=True)

    # Run alembic upgrade head against the new SQLite file.
    sqlite_url = f"sqlite:///{sqlite_file}"
    print(f"Creating fresh SQLite at {sqlite_file}")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{sqlite_file}"
    from alembic import command
    from alembic.config import Config as AlembicConfig

    pkg_root = Path(__file__).resolve().parent.parent / "packages" / "watchtower"
    cfg = AlembicConfig(str(pkg_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(pkg_root / "migrations"))
    command.upgrade(cfg, "head")

    print(f"Reading from {pg_url}")
    pg = psycopg.connect(pg_url)
    pg.row_factory = psycopg.rows.dict_row  # type: ignore[attr-defined]

    sqlite_engine = create_engine(sqlite_url)

    with pg.cursor() as cur, sqlite_engine.begin() as sconn:
        # sessions
        cur.execute("SELECT id, project_slug, started_at, ended_at FROM sessions")
        n = 0
        for row in cur.fetchall():
            sconn.execute(
                text("""
                    INSERT INTO sessions (id, project_slug, started_at, ended_at)
                    VALUES (:id, :slug, :sa, :ea)
                """),
                {
                    "id": _s(row["id"]),
                    "slug": _s(row["project_slug"]),
                    "sa": _epoch(row["started_at"]),
                    "ea": _epoch(row["ended_at"]),
                },
            )
            n += 1
        print(f"  sessions: {n}")

        # messages
        cur.execute("""
            SELECT uuid, message_id, parent_uuid, session_id, project_slug,
                   record_type, model, input_tokens, output_tokens,
                   cache_read_tokens, cache_create_5m_tokens, cache_create_1h_tokens,
                   prompt_text, prompt_chars, is_sidechain, agent_id, recorded_at
            FROM messages
        """)
        n = 0
        for row in cur.fetchall():
            sconn.execute(
                text("""
                    INSERT INTO messages (
                        uuid, message_id, parent_uuid, session_id, project_slug,
                        record_type, model, input_tokens, output_tokens,
                        cache_read_tokens, cache_create_5m_tokens, cache_create_1h_tokens,
                        prompt_text, prompt_chars, is_sidechain, agent_id, recorded_at
                    ) VALUES (
                        :uuid, :mid, :puuid, :sid, :slug, :rtype, :model,
                        :it, :ot, :crt, :cc5, :cc1, :ptxt, :pchars,
                        :sc, :aid, :ra
                    )
                """),
                {
                    "uuid": _s(row["uuid"]),
                    "mid": _s(row["message_id"]),
                    "puuid": _s(row["parent_uuid"]),
                    "sid": _s(row["session_id"]),
                    "slug": _s(row["project_slug"]),
                    "rtype": _s(row["record_type"]),
                    "model": _s(row["model"]),
                    "it": row["input_tokens"],
                    "ot": row["output_tokens"],
                    "crt": row["cache_read_tokens"],
                    "cc5": row["cache_create_5m_tokens"],
                    "cc1": row["cache_create_1h_tokens"],
                    "ptxt": _s(row["prompt_text"]),
                    "pchars": row["prompt_chars"],
                    "sc": _b(row["is_sidechain"]),
                    "aid": _s(row["agent_id"]),
                    "ra": _epoch(row["recorded_at"]),
                },
            )
            n += 1
        print(f"  messages: {n}")

        # tool_calls
        cur.execute("""
            SELECT message_uuid, session_id, tool_name, target,
                   result_tokens, is_error, recorded_at
            FROM tool_calls
        """)
        n = 0
        for row in cur.fetchall():
            sconn.execute(
                text("""
                    INSERT INTO tool_calls
                        (message_uuid, session_id, tool_name, target,
                         result_tokens, is_error, recorded_at)
                    VALUES
                        (:mu, :sid, :name, :tgt, :rt, :err, :ra)
                """),
                {
                    "mu": _s(row["message_uuid"]),
                    "sid": _s(row["session_id"]),
                    "name": _s(row["tool_name"]),
                    "tgt": _s(row["target"]),
                    "rt": row["result_tokens"],
                    "err": _b(row["is_error"]),
                    "ra": _epoch(row["recorded_at"]),
                },
            )
            n += 1
        print(f"  tool_calls: {n}")

    pg.close()
    sqlite_engine.dispose()
    print(f"Done. SQLite file at {sqlite_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
