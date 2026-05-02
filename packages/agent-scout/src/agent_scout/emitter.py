import dataclasses
import logging
from datetime import datetime

import httpx
from beacon.adapters.claude_code import ClaudeCodeAdapter
from beacon.dedup import StreamingDeduplicator
from beacon.schema import TelemetryRecord

logger = logging.getLogger(__name__)


def _serialize(record: TelemetryRecord) -> dict:
    d = dataclasses.asdict(record)
    # datetime → ISO string for JSON
    ts = d.get("timestamp")
    if isinstance(ts, datetime):
        d["timestamp"] = ts.isoformat()
    return d


class Emitter:
    """Parses raw JSONL records via the Beacon adapter and POSTs to Watchtower."""

    def __init__(self, watchtower_url: str, timeout: int = 10) -> None:
        self._url = watchtower_url.rstrip("/") + "/ingest"
        self._timeout = timeout
        self._adapter = ClaudeCodeAdapter()

    def emit(self, raw_records: list[dict], project_slug: str) -> bool:
        """
        Normalize raw_records, deduplicate, and POST to Watchtower.
        Returns True on success, False on failure (caller should NOT advance state).
        """
        dedup = StreamingDeduplicator()
        for raw in raw_records:
            record = self._adapter.parse(raw, project_slug)
            if record is not None:
                dedup.push(record)

        normalized = dedup.flush()
        if not normalized:
            return True  # Nothing to emit — not a failure

        payload = {"records": [_serialize(r) for r in normalized]}
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(self._url, json=payload)
                resp.raise_for_status()
            logger.debug("Emitted %d records to Watchtower", len(normalized))
            return True
        except httpx.HTTPStatusError as e:
            logger.error(
                "Watchtower rejected records: %s %s", e.response.status_code, e.response.text
            )
        except Exception as e:
            logger.error("Failed to reach Watchtower at %s: %s", self._url, e)
        return False
