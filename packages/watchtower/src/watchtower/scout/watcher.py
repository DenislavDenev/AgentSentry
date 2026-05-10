"""In-process JSONL file watcher.

Replaces the standalone agent-scout service. The watchdog observer runs in a
daemon thread; on each file event it schedules `ingest_records` on the
application's asyncio event loop via `run_coroutine_threadsafe`. No queue, no
retry loop — SQLite WAL + busy_timeout absorbs any contention. If a write
fails, the state file is not advanced so the next file event re-delivers;
the existing UNIQUE constraint on `uuid` deduplicates the replay.

Concurrency model:
- `initial_scan_async()` is an async method called from within the event loop
  at startup — it awaits `ingest_records()` directly.
- `_JournalHandler._process()` is called from the watchdog observer thread
  and uses `run_coroutine_threadsafe` + `future.result()` (blocks the
  watchdog thread, not the event loop).
"""

import asyncio
import json
import logging
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from beacon.adapters.claude_code import ClaudeCodeAdapter
from beacon.dedup import StreamingDeduplicator
from beacon.schema import TelemetryRecord
from watchtower.scout.state import StateStore

logger = logging.getLogger(__name__)

_adapter = ClaudeCodeAdapter()


def _to_record_in(rec: TelemetryRecord):
    """Convert a Beacon TelemetryRecord to a watchtower RecordIn."""
    from watchtower.schema.models import RecordIn, ToolCallIn

    return RecordIn(
        uuid=rec.uuid,
        message_id=rec.message_id,
        parent_uuid=rec.parent_uuid,
        session_id=rec.session_id,
        project_slug=rec.project_slug,
        record_type=rec.record_type,
        model=rec.model,
        timestamp=rec.timestamp,
        input_tokens=rec.input_tokens,
        output_tokens=rec.output_tokens,
        cache_read_tokens=rec.cache_read_tokens,
        cache_create_5m_tokens=rec.cache_create_5m_tokens,
        cache_create_1h_tokens=rec.cache_create_1h_tokens,
        tool_calls=[
            ToolCallIn(
                name=tc.name,
                target=tc.target,
                result_tokens=tc.result_tokens,
                is_error=tc.is_error,
            )
            for tc in rec.tool_calls
        ],
        prompt_text=rec.prompt_text,
        prompt_chars=rec.prompt_chars,
        is_sidechain=rec.is_sidechain,
        agent_id=rec.agent_id,
    )


def _parse_file(
    path: Path, data_dir: Path, state: StateStore
) -> tuple[list, int, float] | None:
    """Read new bytes from a JSONL file and return (records_in, new_offset, mtime).

    Returns None if there is nothing new to process. Advances past incomplete
    trailing lines so we only deliver complete records.
    """
    try:
        rel = str(path.relative_to(data_dir))
    except ValueError:
        return None

    parts = Path(rel).parts
    if len(parts) < 3 or parts[0] != "projects":
        logger.debug("Ignoring JSONL outside projects/: %s", rel)
        return None
    project_slug = parts[1]

    file_state = state.get(rel)
    offset = file_state.bytes_read if file_state else 0

    try:
        with path.open("rb") as f:
            f.seek(offset)
            data = f.read()
    except OSError as e:
        logger.error("Cannot read %s: %s", path, e)
        return None

    if not data:
        return None

    last_newline = data.rfind(b"\n")
    if last_newline == -1:
        return None  # No complete line yet

    complete = data[: last_newline + 1]
    new_offset = offset + last_newline + 1

    raw_records: list[dict] = []
    for line in complete.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw_records.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("Malformed JSONL line in %s (offset ~%d)", path, offset)

    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0

    if not raw_records:
        # Advance state past whitespace-only lines.
        state.update(rel, new_offset, mtime)
        return None

    dedup = StreamingDeduplicator()
    for raw in raw_records:
        record = _adapter.parse(raw, project_slug)
        if record is not None:
            dedup.push(record)

    normalized = dedup.flush()
    if not normalized:
        state.update(rel, new_offset, mtime)
        return None

    records_in = [_to_record_in(r) for r in normalized]
    return records_in, new_offset, mtime


class _JournalHandler(FileSystemEventHandler):
    """Called from the watchdog observer thread."""

    def __init__(
        self, agent_data_dir: Path, state: StateStore, loop: asyncio.AbstractEventLoop
    ) -> None:
        self._data_dir = agent_data_dir
        self._state = state
        self._loop = loop

    def on_modified(self, event) -> None:
        if not isinstance(event, (FileModifiedEvent, FileCreatedEvent)):
            return
        path = Path(event.src_path)
        if path.suffix == ".jsonl":
            self._process_from_thread(path)

    on_created = on_modified

    def _process_from_thread(self, path: Path) -> None:
        """Parse the file and schedule ingest on the event loop from this thread."""
        from watchtower.router.ingest import ingest_records

        result = _parse_file(path, self._data_dir, self._state)
        if result is None:
            return

        records_in, new_offset, mtime = result
        rel = str(path.relative_to(self._data_dir))

        future = asyncio.run_coroutine_threadsafe(ingest_records(records_in), self._loop)
        try:
            future.result(timeout=30)
            self._state.update(rel, new_offset, mtime)
        except Exception as e:
            logger.error("Ingest failed for %s; will retry on next file event: %s", rel, e)
            # State NOT advanced — next event re-delivers; dedup catches duplicates.


class Scout:
    """In-process replacement for the agent-scout service."""

    def __init__(
        self, agent_data_dir: Path, state: StateStore, loop: asyncio.AbstractEventLoop
    ) -> None:
        self._data_dir = agent_data_dir
        self._state = state
        self._loop = loop
        self._handler = _JournalHandler(agent_data_dir, state, loop)
        self._observer = Observer()

    async def initial_scan_async(self) -> None:
        """Process all existing JSONL files on startup.

        Called from within the running event loop (await scout.initial_scan_async()),
        so we can directly await ingest_records() without run_coroutine_threadsafe.
        """
        from watchtower.router.ingest import ingest_records

        projects_dir = self._data_dir / "projects"
        if not projects_dir.exists():
            logger.info("Projects directory not found: %s", projects_dir)
            return

        count = 0
        for path in projects_dir.rglob("*.jsonl"):
            result = _parse_file(path, self._data_dir, self._state)
            if result is None:
                continue
            records_in, new_offset, mtime = result
            rel = str(path.relative_to(self._data_dir))
            try:
                await ingest_records(records_in)
                self._state.update(rel, new_offset, mtime)
                count += len(records_in)
            except Exception as e:
                logger.error("Initial scan ingest failed for %s: %s", rel, e)

        logger.info("Initial scan complete — ingested %d records", count)

    def start(self) -> None:
        self._observer.schedule(self._handler, str(self._data_dir), recursive=True)
        self._observer.start()
        logger.info("Scout watching %s", self._data_dir)

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
