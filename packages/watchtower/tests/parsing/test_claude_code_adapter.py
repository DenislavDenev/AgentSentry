from watchtower.parsing.adapters.claude_code import ClaudeCodeAdapter

ADAPTER = ClaudeCodeAdapter()
SLUG = "test-project"


def _assistant(message_id="msg_abc", model="claude-sonnet-4-6", **usage):
    defaults = dict(
        input_tokens=10,
        output_tokens=20,
        cache_read_input_tokens=0,
        cache_creation={"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 0},
    )
    defaults.update(usage)
    return {
        "uuid": "uuid-1",
        "type": "assistant",
        "sessionId": "sess-1",
        "timestamp": "2025-01-01T00:00:00Z",
        "message": {
            "id": message_id,
            "model": model,
            "content": [],
            "usage": defaults,
        },
    }


def test_assistant_tokens():
    rec = ADAPTER.parse(_assistant(input_tokens=100, output_tokens=50), SLUG)
    assert rec is not None
    assert rec.input_tokens == 100
    assert rec.output_tokens == 50
    assert rec.record_type == "assistant"
    assert rec.model == "claude-sonnet-4-6"
    assert rec.message_id == "msg_abc"


def test_missing_tokens_default_to_zero():
    raw = {
        "uuid": "u1",
        "type": "assistant",
        "sessionId": "s1",
        "timestamp": "2025-01-01T00:00:00Z",
        "message": {"id": "m1", "model": "claude-opus-4-7", "content": [], "usage": {}},
    }
    rec = ADAPTER.parse(raw, SLUG)
    assert rec is not None
    assert rec.input_tokens == 0
    assert rec.output_tokens == 0
    assert rec.cache_read_tokens == 0


def test_cache_tokens():
    raw = _assistant(
        cache_creation={"ephemeral_5m_input_tokens": 500, "ephemeral_1h_input_tokens": 200},
        cache_read_input_tokens=100,
    )
    rec = ADAPTER.parse(raw, SLUG)
    assert rec.cache_read_tokens == 100
    assert rec.cache_create_5m_tokens == 500
    assert rec.cache_create_1h_tokens == 200


def test_tool_use_extraction():
    raw = {
        "uuid": "u2",
        "type": "assistant",
        "sessionId": "s1",
        "timestamp": "2025-01-01T00:00:00Z",
        "message": {
            "id": "m2",
            "model": "claude-sonnet-4-6",
            "content": [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "Read",
                    "input": {"file_path": "/foo/bar.py"},
                },  # noqa: E501
                {"type": "tool_use", "id": "t2", "name": "Bash", "input": {"command": "ls -la"}},
            ],
            "usage": {"input_tokens": 5, "output_tokens": 3},
        },
    }
    rec = ADAPTER.parse(raw, SLUG)
    assert len(rec.tool_calls) == 2
    assert rec.tool_calls[0].name == "Read"
    assert rec.tool_calls[0].target == "/foo/bar.py"
    assert rec.tool_calls[1].name == "Bash"
    assert rec.tool_calls[1].target == "ls -la"


def test_tool_result_estimation():
    body = "x" * 400
    raw = {
        "uuid": "u3",
        "type": "user",
        "sessionId": "s1",
        "timestamp": "2025-01-01T00:00:00Z",
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "t1", "content": body}],
        },
    }
    rec = ADAPTER.parse(raw, SLUG)
    assert rec is not None
    assert len(rec.tool_calls) == 1
    assert rec.tool_calls[0].name == "_tool_result"
    assert rec.tool_calls[0].result_tokens == 100  # 400 chars // 4


def test_user_prompt_text():
    raw = {
        "uuid": "u4",
        "type": "user",
        "sessionId": "s1",
        "timestamp": "2025-01-01T00:00:00Z",
        "message": {"role": "user", "content": "hello world"},
    }
    rec = ADAPTER.parse(raw, SLUG)
    assert rec is not None
    assert rec.prompt_text == "hello world"
    assert rec.prompt_chars == 11


def test_meta_user_skipped():
    raw = {
        "uuid": "u5",
        "type": "user",
        "isMeta": True,
        "sessionId": "s1",
        "timestamp": "2025-01-01T00:00:00Z",
        "message": {"role": "user", "content": "system metadata"},
    }
    assert ADAPTER.parse(raw, SLUG) is None


def test_system_records_skipped():
    raw = {"uuid": "u6", "type": "system", "sessionId": "s1", "timestamp": "2025-01-01T00:00:00Z"}
    assert ADAPTER.parse(raw, SLUG) is None


def test_missing_uuid_skipped():
    raw = {
        "type": "assistant",
        "sessionId": "s1",
        "timestamp": "2025-01-01T00:00:00Z",
        "message": {},
    }  # noqa: E501
    assert ADAPTER.parse(raw, SLUG) is None


def test_timestamp_parsed():
    rec = ADAPTER.parse(_assistant(), SLUG)
    assert rec.timestamp.tzinfo is not None
    assert rec.timestamp.year == 2025
