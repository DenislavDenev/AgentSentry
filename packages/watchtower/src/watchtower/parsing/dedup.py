from watchtower.parsing.schema import TelemetryRecord


class StreamingDeduplicator:
    """
    Last-wins deduplication for Claude Code streaming snapshots.

    Claude Code writes the same API response 2-3 times while streaming,
    each with a distinct top-level `uuid` but the same `message.id`.
    Within a flush batch, the last record for a given (session_id, message_id)
    pair is kept and the earlier snapshots are discarded.

    Cross-batch deduplication is handled by Watchtower's DB upsert on
    (session_id, message_id).
    """

    def __init__(self) -> None:
        # Records without a message_id cannot be deduped — stored by uuid instead
        self._keyed: dict[tuple[str, str], TelemetryRecord] = {}
        self._unkeyed: list[TelemetryRecord] = []

    def push(self, record: TelemetryRecord) -> None:
        if record.message_id is not None:
            key = (record.session_id, record.message_id)
            self._keyed[key] = record
        else:
            self._unkeyed.append(record)

    def flush(self) -> list[TelemetryRecord]:
        result = list(self._keyed.values()) + self._unkeyed
        self._keyed.clear()
        self._unkeyed.clear()
        return result
