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

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" })
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  overview: () => get<OverviewStats>("/stats/overview"),
  daily: (days = 30) => get<DailyStats[]>(`/stats/daily?days=${days}`),
  sessions: (limit = 50, offset = 0) =>
    get<SessionSummary[]>(`/sessions?limit=${limit}&offset=${offset}`),
  session: (id: string) => get<SessionDetail>(`/sessions/${id}`),
  projects: () => get<ProjectSummary[]>("/projects"),
  project: (slug: string) =>
    get<ProjectDetail>(`/projects/${encodeURIComponent(slug)}`),
  models: () => get<ModelStat[]>("/models"),
  tools: () => get<ToolStat[]>("/tools"),
  prompts: (limit = 50) => get<PromptStat[]>(`/prompts?limit=${limit}`),
}
