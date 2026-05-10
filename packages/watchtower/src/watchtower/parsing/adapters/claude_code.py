import logging
from datetime import UTC, datetime

from watchtower.parsing.adapters.base import BaseAdapter
from watchtower.parsing.schema import TelemetryRecord, ToolCall

logger = logging.getLogger(__name__)

# Maps tool name → the input field that represents the primary target
_TARGET_FIELDS: dict[str, str] = {
    "Read": "file_path",
    "Edit": "file_path",
    "Write": "file_path",
    "Glob": "pattern",
    "Grep": "pattern",
    "Bash": "command",
    "WebFetch": "url",
    "WebSearch": "query",
    "Task": "subagent_type",
    "Skill": "skill",
}
_TARGET_MAX_CHARS = 500

# Basenames of Codex launcher scripts.  Add new names here if the companion
# is renamed — this is the single place that needs updating.
_CODEX_LAUNCHERS = frozenset(["codex-companion.mjs"])


def is_codex_invocation(command: str) -> bool:
    """Return True if any whitespace-delimited token in `command` is a known
    Codex launcher script.

    Simple basename match — no shell tokenizer needed since the file name is
    distinctive enough that false positives are impossible in practice.
    """
    from pathlib import PurePath

    for token in command.split():
        try:
            if PurePath(token).name in _CODEX_LAUNCHERS:
                return True
        except Exception:
            pass
    return False


# Record types that carry no telemetry value
_SKIP_TYPES = frozenset(
    [
        "system",
        "queue-operation",
        "attachment",
        "ai-title",
        "last-prompt",
        "summary",
    ]
)


def _parse_timestamp(raw: str) -> datetime:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(UTC)


def _usage_tokens(record: dict) -> dict[str, int]:
    u = (record.get("message") or {}).get("usage") or {}
    cc = u.get("cache_creation") or {}
    return {
        "input_tokens": int(u.get("input_tokens") or 0),
        "output_tokens": int(u.get("output_tokens") or 0),
        "cache_read_tokens": int(u.get("cache_read_input_tokens") or 0),
        "cache_create_5m_tokens": int(cc.get("ephemeral_5m_input_tokens") or 0),
        "cache_create_1h_tokens": int(cc.get("ephemeral_1h_input_tokens") or 0),
    }


def _tool_target(name: str, inp: dict) -> str:
    field = _TARGET_FIELDS.get(name)
    value = inp.get(field, "") if field else ""
    return str(value)[:_TARGET_MAX_CHARS]


def _extract_tool_uses(content: list) -> list[ToolCall]:
    calls = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = block.get("name") or "unknown"
        target = _tool_target(name, block.get("input") or {})
        calls.append(ToolCall(name=name, target=target, result_tokens=0, is_error=False))
    return calls


def _extract_tool_results(content: list) -> list[ToolCall]:
    results = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        body = block.get("content")
        if isinstance(body, str):
            chars = len(body)
        elif isinstance(body, list):
            chars = sum(len(p.get("text", "")) for p in body if isinstance(p, dict))
        else:
            chars = 0
        result_tokens = chars // 4
        is_error = bool(block.get("is_error"))
        results.append(
            ToolCall(name="_tool_result", target="", result_tokens=result_tokens, is_error=is_error)
        )
    return results


def _prompt_text(content) -> tuple[str | None, int | None]:
    if isinstance(content, str):
        return (content, len(content)) if content else (None, None)
    if isinstance(content, list):
        parts = [
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        ]
        text = "".join(parts) or None
        return (text, len(text)) if text else (None, None)
    return None, None


class ClaudeCodeAdapter(BaseAdapter):
    def parse(self, record: dict, project_slug: str) -> TelemetryRecord | None:
        rec_type = record.get("type")
        if rec_type in _SKIP_TYPES:
            return None

        uuid = record.get("uuid")
        session_id = record.get("sessionId")
        timestamp_raw = record.get("timestamp", "")

        if not uuid or not session_id:
            return None

        timestamp = _parse_timestamp(timestamp_raw)
        parent_uuid = record.get("parentUuid")
        is_sidechain = bool(record.get("isSidechain"))
        agent_id = record.get("agentId")

        if rec_type == "assistant":
            msg = record.get("message") or {}
            message_id = msg.get("id")
            model = msg.get("model")
            tokens = _usage_tokens(record)
            content = msg.get("content") or []
            tool_calls = _extract_tool_uses(content)
            # Tag records that invoke the Codex companion so the prompts page
            # can filter by source.  Check every Bash tool call's command string.
            tags: list[str] = []
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                if block.get("name") == "Bash":
                    cmd = (block.get("input") or {}).get("command", "")
                    if cmd and is_codex_invocation(cmd):
                        tags = ["codex"]
                        break
            return TelemetryRecord(
                uuid=uuid,
                message_id=message_id,
                parent_uuid=parent_uuid,
                session_id=session_id,
                project_slug=project_slug,
                record_type="assistant",
                timestamp=timestamp,
                model=model,
                tool_calls=tool_calls,
                is_sidechain=is_sidechain,
                agent_id=agent_id,
                tags=tags,
                **tokens,
            )

        if rec_type == "user":
            # Skip metadata messages (permission prompts, tool results injected by the harness)
            if record.get("isMeta"):
                return None
            msg = record.get("message") or {}
            content = msg.get("content")
            # If content is a list containing only tool_result blocks, it's a tool result message
            if isinstance(content, list):
                tool_calls = _extract_tool_results(content)
                if tool_calls:
                    return TelemetryRecord(
                        uuid=uuid,
                        message_id=None,
                        parent_uuid=parent_uuid,
                        session_id=session_id,
                        project_slug=project_slug,
                        record_type="user",
                        timestamp=timestamp,
                        tool_calls=tool_calls,
                        is_sidechain=is_sidechain,
                        agent_id=agent_id,
                    )
            # Plain text user prompt
            text, chars = _prompt_text(content)
            if text is None:
                return None
            return TelemetryRecord(
                uuid=uuid,
                message_id=None,
                parent_uuid=parent_uuid,
                session_id=session_id,
                project_slug=project_slug,
                record_type="user",
                timestamp=timestamp,
                prompt_text=text,
                prompt_chars=chars,
                is_sidechain=is_sidechain,
                agent_id=agent_id,
            )

        logger.debug("Skipping unknown record type: %s", rec_type)
        return None
