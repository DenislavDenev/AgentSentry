import type {
  DailyStats,
  ModelStat,
  OverviewStats,
  ProjectDetail,
  ProjectSummary,
  PromptStat,
  SessionDetail,
  SessionSummary,
  ToolStat,
} from "@/lib/types"

// Always use /api — the Vite dev proxy rewrites to localhost:8000,
// and in production watchtower serves both the SPA and the API under /api.
async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`, { cache: "no-store" })
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  overview: (days = 0) => get<OverviewStats>(`/stats/overview?days=${days}`),
  daily: (days = 30) => get<DailyStats[]>(`/stats/daily?days=${days}`),
  sessions: (limit = 50, offset = 0, days = 0) =>
    get<SessionSummary[]>(`/sessions?limit=${limit}&offset=${offset}&days=${days}`),
  session: (id: string) => get<SessionDetail>(`/sessions/${id}`),
  projects: (days = 0) => get<ProjectSummary[]>(`/projects?days=${days}`),
  project: (slug: string) =>
    get<ProjectDetail>(`/projects/${encodeURIComponent(slug)}`),
  models: (days = 0) => get<ModelStat[]>(`/models?days=${days}`),
  tools: (days = 0) => get<ToolStat[]>(`/tools?days=${days}`),
  prompts: (limit = 50, days = 0) =>
    get<PromptStat[]>(`/prompts?limit=${limit}&days=${days}`),
}
