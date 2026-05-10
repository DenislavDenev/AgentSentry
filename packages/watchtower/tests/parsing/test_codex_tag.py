"""Tests for Codex plugin invocation detection.

Covers is_codex_invocation() and verifies that TelemetryRecord.tags is
populated correctly by ClaudeCodeAdapter.parse().
"""

import pytest
from watchtower.parsing.adapters.claude_code import ClaudeCodeAdapter, is_codex_invocation


# ---------------------------------------------------------------------------
# is_codex_invocation — pure function, no adapter needed
# ---------------------------------------------------------------------------

POSITIVE_CASES = [
    # Typical node invocation with absolute path
    'node /home/user/.claude/plugins/cache/openai-codex/codex/1.0.4/scripts/codex-companion.mjs review .',
    # Windows-style path with backslashes (PurePath normalises them)
    r'node C:\Users\Foo\.claude\plugins\cache\openai-codex\codex\1.0.4\scripts\codex-companion.mjs review .',
    # Relative path
    'node ./scripts/codex-companion.mjs --wait',
    # Bare basename (unlikely but valid)
    'node codex-companion.mjs',
    # Extra flags before the script
    'node --experimental-vm-modules /opt/codex/codex-companion.mjs adversarial-review',
]

NEGATIVE_CASES = [
    # No companion script at all
    'bash -c "echo hello"',
    # Different script name
    'node some-other-companion.mjs',
    # Empty string
    '',
    # Just whitespace
    '   ',
    # companion in a directory name, not basename
    'node /codex-companion.mjs/something.js',
]


@pytest.mark.parametrize("cmd", POSITIVE_CASES)
def test_is_codex_invocation_positive(cmd):
    assert is_codex_invocation(cmd) is True, f"Expected True for: {cmd!r}"


@pytest.mark.parametrize("cmd", NEGATIVE_CASES)
def test_is_codex_invocation_negative(cmd):
    assert is_codex_invocation(cmd) is False, f"Expected False for: {cmd!r}"


# ---------------------------------------------------------------------------
# ClaudeCodeAdapter.parse — verifies tags are populated on the record
# ---------------------------------------------------------------------------

_ADAPTER = ClaudeCodeAdapter()

_BASE_ASSISTANT = {
    "type": "assistant",
    "uuid": "uuid-1",
    "sessionId": "sess-1",
    "timestamp": "2025-06-01T10:00:00Z",
    "parentUuid": None,
    "isSidechain": False,
    "agentId": None,
    "message": {
        "id": "msg-1",
        "model": "claude-sonnet-4-6",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_input_tokens": 0,
            "cache_creation": {},
        },
        "content": [],
    },
}


def _with_bash_tool(command: str) -> dict:
    rec = dict(_BASE_ASSISTANT)
    rec["message"] = dict(_BASE_ASSISTANT["message"])
    rec["message"]["content"] = [
        {
            "type": "tool_use",
            "name": "Bash",
            "input": {"command": command},
        }
    ]
    return rec


def test_tags_set_when_codex_companion_invoked():
    record = _with_bash_tool(
        "node /home/user/.claude/plugins/codex-companion.mjs adversarial-review ."
    )
    result = _ADAPTER.parse(record, "my-project")
    assert result is not None
    assert result.tags == ["codex"]


def test_tags_empty_for_non_codex_bash():
    record = _with_bash_tool("bash -c 'echo hello'")
    result = _ADAPTER.parse(record, "my-project")
    assert result is not None
    assert result.tags == []


def test_tags_empty_when_no_tool_calls():
    result = _ADAPTER.parse(_BASE_ASSISTANT, "my-project")
    assert result is not None
    assert result.tags == []


def test_tags_empty_for_non_bash_tool():
    rec = dict(_BASE_ASSISTANT)
    rec["message"] = dict(_BASE_ASSISTANT["message"])
    rec["message"]["content"] = [
        {
            "type": "tool_use",
            "name": "Read",
            "input": {"file_path": "/home/user/.claude/plugins/codex-companion.mjs"},
        }
    ]
    result = _ADAPTER.parse(rec, "my-project")
    assert result is not None
    # Read tool, not Bash — should not trigger Codex tag
    assert result.tags == []


def test_tags_set_on_first_codex_tool_only():
    """Multiple Bash calls: first is Codex, second is not. Tags should be ['codex']."""
    rec = dict(_BASE_ASSISTANT)
    rec["message"] = dict(_BASE_ASSISTANT["message"])
    rec["message"]["content"] = [
        {"type": "tool_use", "name": "Bash", "input": {"command": "node codex-companion.mjs review ."}},
        {"type": "tool_use", "name": "Bash", "input": {"command": "echo done"}},
    ]
    result = _ADAPTER.parse(rec, "my-project")
    assert result is not None
    assert result.tags == ["codex"]
