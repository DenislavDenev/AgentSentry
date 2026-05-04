from datetime import datetime

from pydantic import BaseModel


class ToolCallIn(BaseModel):
    name: str
    target: str = ""
    result_tokens: int = 0
    is_error: bool = False


class RecordIn(BaseModel):
    uuid: str
    message_id: str | None = None
    parent_uuid: str | None = None
    session_id: str
    project_slug: str
    record_type: str
    model: str | None = None
    timestamp: datetime
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_create_5m_tokens: int = 0
    cache_create_1h_tokens: int = 0
    tool_calls: list[ToolCallIn] = []
    prompt_text: str | None = None
    prompt_chars: int | None = None
    is_sidechain: bool = False
    agent_id: str | None = None
    source: str = "claude-code"


class IngestRequest(BaseModel):
    records: list[RecordIn]


class SessionSummary(BaseModel):
    id: str
    project_slug: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_secs: int | None
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    total_tokens: int
    message_count: int


class MessageOut(BaseModel):
    uuid: str
    message_id: str | None
    parent_uuid: str | None = None
    record_type: str
    model: str | None
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_create_5m_tokens: int
    cache_create_1h_tokens: int
    prompt_text: str | None
    prompt_chars: int | None
    is_sidechain: bool
    agent_id: str | None
    recorded_at: datetime


class SessionDetail(SessionSummary):
    messages: list[MessageOut]


class ProjectSummary(BaseModel):
    slug: str
    session_count: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    total_tokens: int


class DailyStats(BaseModel):
    date: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_create_tokens: int
    total_tokens: int
    session_count: int


class ProjectDetail(ProjectSummary):
    daily: list[DailyStats]


class OverviewStats(BaseModel):
    total_sessions: int
    total_messages: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_create_5m_tokens: int
    cache_create_1h_tokens: int
    total_tokens: int
    cache_efficiency_pct: float


class ModelStat(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    message_count: int


class ToolStat(BaseModel):
    tool_name: str
    invocation_count: int
    result_tokens: int
    error_count: int
    error_rate_pct: float


class PromptStat(BaseModel):
    uuid: str
    session_id: str
    project_slug: str
    prompt_text: str
    prompt_chars: int
    input_tokens: int  # assistant response input tokens (0 if no response yet)
    output_tokens: int
    cache_create_tokens: int
    billable_tokens: int  # total billable cost of the triggered assistant response
    recorded_at: str
