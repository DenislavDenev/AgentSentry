import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FileState:
    bytes_read: int
    mtime: float


class StateStore:
    """Persists per-file high-water marks so rescans only process new content."""

    def __init__(self, state_dir: Path) -> None:
        state_dir.mkdir(parents=True, exist_ok=True)
        self._path = state_dir / "scout-state.json"
        self._state: dict[str, FileState] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self._state = {k: FileState(**v) for k, v in data.items()}
        except Exception:
            logger.warning("Could not load state file %s; starting fresh", self._path)

    def _save(self) -> None:
        try:
            data = {k: asdict(v) for k, v in self._state.items()}
            self._path.write_text(json.dumps(data, indent=2))
        except Exception:
            logger.error("Failed to save state to %s", self._path)

    def get(self, rel_path: str) -> FileState | None:
        return self._state.get(rel_path)

    def update(self, rel_path: str, bytes_read: int, mtime: float) -> None:
        self._state[rel_path] = FileState(bytes_read=bytes_read, mtime=mtime)
        self._save()
