import { DailyBarChart } from "@/components/charts/DailyBarChart"
import { ModelPieChart } from "@/components/charts/ModelPieChart"
import { ProjectsBarChart } from "@/components/charts/ProjectsBarChart"
import { ToolsBarChart } from "@/components/charts/ToolsBarChart"
import { SessionsTable } from "@/components/tables/SessionsTable"
import { StatCard } from "@/components/ui/StatCard"
import { api } from "@/lib/api"
import { fmtCost, fmtPct, fmtTokens } from "@/lib/format"
import { calcCostGeneric } from "@/lib/pricing"

export default async function OverviewPage() {
  const [overview, daily, models, sessions, projects, tools] = await Promise.all([
    api.overview().catch(() => null),
    api.daily(30).catch(() => []),
    api.models().catch(() => []),
    api.sessions(10).catch(() => []),
    api.projects().catch(() => []),
    api.tools().catch(() => []),
  ])

  // Plan is client-side (localStorage); SSR defaults to "api" for cost display
  const plan = "api" as const

  const stats = overview ?? {
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

  const cacheCreateTotal = stats.cache_create_5m_tokens + stats.cache_create_1h_tokens
  const estimatedCost = calcCostGeneric(
    stats.input_tokens,
    stats.output_tokens,
    stats.cache_read_tokens,
    plan,
  )

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Overview</h1>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Total tokens" value={fmtTokens(stats.total_tokens)} />
        <StatCard label="Sessions" value={String(stats.total_sessions)} />
        <StatCard label="Messages" value={String(stats.total_messages)} />
        <StatCard
          label="Cache efficiency"
          value={fmtPct(stats.cache_efficiency_pct)}
          sub="reads / (input + reads)"
        />
        <StatCard
          label="Cache created"
          value={fmtTokens(cacheCreateTotal)}
          sub="5m + 1h tokens"
        />
        <StatCard
          label="Est. cost"
          value={plan === "api" ? fmtCost(estimatedCost) : "N/A"}
          sub={plan === "api" ? "API rates · Sonnet" : "Subscription plan"}
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
            Top projects by token spend
          </h2>
          <ProjectsBarChart data={projects} />
        </div>
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
          <h2 className="mb-3 text-sm font-medium text-gray-400">Top tools by invocations</h2>
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
