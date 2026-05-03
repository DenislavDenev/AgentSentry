import { DailyBarChart } from "@/components/charts/DailyBarChart"
import { ModelPieChart } from "@/components/charts/ModelPieChart"
import { ProjectsBarChart } from "@/components/charts/ProjectsBarChart"
import { ToolsBarChart } from "@/components/charts/ToolsBarChart"
import { SessionsTable } from "@/components/tables/SessionsTable"
import { CostCard } from "@/components/ui/CostCard"
import { StatCard } from "@/components/ui/StatCard"
import { api } from "@/lib/api"
import { fmtPct, fmtTokens } from "@/lib/format"

export default async function OverviewPage() {
  const [overview, daily, models, sessions, projects, tools] = await Promise.all([
    api.overview().catch(() => null),
    api.daily(30).catch(() => []),
    api.models().catch(() => []),
    api.sessions(10).catch(() => []),
    api.projects().catch(() => []),
    api.tools().catch(() => []),
  ])

  const s = overview ?? {
    total_sessions: 0,
    total_messages: 0,
    input_tokens: 0,
    output_tokens: 0,
    cache_read_tokens: 0,
    cache_create_5m_tokens: 0,
    cache_create_1h_tokens: 0,
    total_tokens: 0,
    cache_efficiency_pct: 0,
  }

  const cacheCreate = s.cache_create_5m_tokens + s.cache_create_1h_tokens

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Overview</h1>

      {/* 7 KPI cards matching token-dashboard */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
        <StatCard label="Sessions" value={String(s.total_sessions)} />
        <StatCard label="Turns" value={String(s.total_messages)} sub="messages" />
        <StatCard label="Input tokens" value={fmtTokens(s.input_tokens)} />
        <StatCard label="Output tokens" value={fmtTokens(s.output_tokens)} />
        <StatCard label="Cache read" value={fmtTokens(s.cache_read_tokens)} />
        <StatCard label="Cache write" value={fmtTokens(cacheCreate)} sub="5m + 1h" />
        <CostCard
          inputTokens={s.input_tokens}
          outputTokens={s.output_tokens}
          cacheReadTokens={s.cache_read_tokens}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
          <h2 className="mb-3 text-sm font-medium text-gray-400">Daily tokens (30 days)</h2>
          <DailyBarChart data={daily} />
        </div>
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
          <h2 className="mb-3 text-sm font-medium text-gray-400">Token share by model</h2>
          <ModelPieChart data={models} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
          <h2 className="mb-3 text-sm font-medium text-gray-400">
            Top projects · token spend
          </h2>
          <ProjectsBarChart data={projects} />
        </div>
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
          <h2 className="mb-3 text-sm font-medium text-gray-400">Top tools · invocations</h2>
          <ToolsBarChart data={tools} />
        </div>
      </div>

      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <h2 className="mb-3 text-sm font-medium text-gray-400">Recent sessions</h2>
        <SessionsTable sessions={sessions} />
      </div>
    </div>
  )
}
