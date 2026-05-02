import json
import logging
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from agent_scout.emitter import Emitter
from agent_scout.state import StateStore

logger = logging.getLogger(__name__)


class _JournalHandler(FileSystemEventHandler):
    def __init__(self, agent_data_dir: Path, state: StateStore, emitter: Emitter) -> None:
        self._data_dir = agent_data_dir
        self._state = state
        self._emitter = emitter

    def on_modified(self, event) -> None:
        if not isinstance(event, (FileModifiedEvent, FileCreatedEvent)):
            return
        path = Path(event.src_path)
        if path.suffix == ".jsonl":
            self._process(path)

    on_created = on_modified

    def _process(self, path: Path) -> None:
        try:
            rel = str(path.relative_to(self._data_dir))
        except ValueError:
            return

        # Extract project_slug from projects/<slug>/<session>.jsonl
        parts = Path(rel).parts
        if len(parts) < 3 or parts[0] != "projects":
            logger.debug("Ignoring JSONL outside projects/: %s", rel)
            return
        project_slug = parts[1]

        state = self._state.get(rel)
        offset = state.bytes_read if state else 0

        try:
            with path.open("rb") as f:
                f.seek(offset)
                data = f.read()
        except OSError as e:
            logger.error("Cannot read %s: %s", path, e)
            return

        if not data:
            return

        last_newline = data.rfind(b"\n")
        if last_newline == -1:
            return  # No complete line yet — wait for more data

        complete = data[: last_newline + 1]
        new_offset = offset + last_newline + 1

        records: list[dict] = []
        for line in complete.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Malformed JSONL line in %s (offset ~%d)", path, offset)

        if not records:
            self._state.update(rel, new_offset, path.stat().st_mtime)
            return

        success = self._emitter.emit(records, project_slug)
        if success:
            self._state.update(rel, new_offset, path.stat().st_mtime)
        else:
            logger.warning("Emit failed for %s; will retry on next change", rel)


class Watcher:
    def __init__(self, agent_data_dir: Path, state: StateStore, emitter: Emitter) -> None:
        self._data_dir = agent_data_dir
        self._state = state
        self._emitter = emitter
        self._handler = _JournalHandler(agent_data_dir, state, emitter)
        self._observer = Observer()

    def initial_scan(self) -> None:
        """Process all existing JSONL files from their high-water mark on startup."""
        projects_dir = self._data_dir / "projects"
        if not projects_dir.exists():
            logger.info("Projects directory not found: %s", projects_dir)
            return
        for path in projects_dir.rglob("*.jsonl"):
            self._handler._process(path)
        logger.info("Initial scan complete")

    def start(self) -> None:
        self._observer.schedule(self._handler, str(self._data_dir), recursive=True)
        self._observer.start()
        logger.info("Watching %s", self._data_dir)

    def join(self) -> None:
        self._observer.join()

    def stop(self) -> None:
        self._observer.stop()
