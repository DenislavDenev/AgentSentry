from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ToolCall:
    name: str
    target: str
    result_tokens: int
    is_error: bool


@dataclass
class TelemetryRecord:
    uuid: str
    session_id: str
    project_slug: str
    record_type: str  # "assistant" | "user"
    timestamp: datetime
    message_id: str | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_create_5m_tokens: int = 0
    cache_create_1h_tokens: int = 0
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_text: str | None = None
    prompt_chars: int | None = None
    is_sidechain: bool = False
    agent_id: str | None = None
    source: str = "claude-code"
