from datetime import UTC, datetime

from beacon.dedup import StreamingDeduplicator
from beacon.schema import TelemetryRecord


def _record(uuid, message_id, session="s1", output_tokens=10):
    return TelemetryRecord(
        uuid=uuid,
        message_id=message_id,
        session_id=session,
        project_slug="proj",
        record_type="assistant",
        timestamp=datetime.now(UTC),
        output_tokens=output_tokens,
    )


def test_single_record_passes_through():
    d = StreamingDeduplicator()
    r = _record("u1", "m1")
    d.push(r)
    assert d.flush() == [r]


def test_streaming_dedup_last_wins():
    d = StreamingDeduplicator()
    r1 = _record("u1", "m1", output_tokens=27)
    r2 = _record("u2", "m1", output_tokens=150)
    r3 = _record("u3", "m1", output_tokens=303)
    d.push(r1)
    d.push(r2)
    d.push(r3)
    result = d.flush()
    assert len(result) == 1
    assert result[0].uuid == "u3"
    assert result[0].output_tokens == 303


def test_different_message_ids_kept_separate():
    d = StreamingDeduplicator()
    d.push(_record("u1", "m1"))
    d.push(_record("u2", "m2"))
    assert len(d.flush()) == 2


def test_different_sessions_not_deduped():
    d = StreamingDeduplicator()
    d.push(_record("u1", "m1", session="s1"))
    d.push(_record("u2", "m1", session="s2"))
    assert len(d.flush()) == 2


def test_none_message_id_not_deduped():
    d = StreamingDeduplicator()
    r1 = _record("u1", None)
    r2 = _record("u2", None)
    d.push(r1)
    d.push(r2)
    result = d.flush()
    assert len(result) == 2


def test_flush_resets_state():
    d = StreamingDeduplicator()
    d.push(_record("u1", "m1"))
    d.flush()
    assert d.flush() == []
