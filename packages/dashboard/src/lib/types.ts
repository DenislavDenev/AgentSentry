export interface SessionSummary {
  id: string
  project_slug: string
  started_at: string | null
  ended_at: string | null
  duration_secs: number | null
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  total_tokens: number
  message_count: number
}

export interface MessageOut {
  uuid: string
  message_id: string | null
  record_type: string
  model: string | null
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_create_5m_tokens: number
  cache_create_1h_tokens: number
  prompt_text: string | null
  prompt_chars: number | null
  is_sidechain: boolean
  agent_id: string | null
  recorded_at: string
}

export interface SessionDetail extends SessionSummary {
  messages: MessageOut[]
}

export interface ProjectSummary {
  slug: string
  session_count: number
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  total_tokens: number
}

export interface DailyStats {
  date: string
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  total_tokens: number
  session_count: number
}

export interface ProjectDetail extends ProjectSummary {
  daily: DailyStats[]
}

export interface OverviewStats {
  total_sessions: number
  total_messages: number
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  total_tokens: number
  cache_efficiency_pct: number
}

export interface ModelStat {
  model: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  message_count: number
}

export interface ToolStat {
  tool_name: string
  invocation_count: number
  result_tokens: number
  error_count: number
  error_rate_pct: number
}

export interface PromptStat {
  uuid: string
  session_id: string
  project_slug: string
  prompt_text: string
  prompt_chars: number
  recorded_at: string
}
