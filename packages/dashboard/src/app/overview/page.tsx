import { DailyBarChart } from "@/components/charts/DailyBarChart"
import { ModelPieChart } from "@/components/charts/ModelPieChart"
import { SessionsTable } from "@/components/tables/SessionsTable"
import { StatCard } from "@/components/ui/StatCard"
import { api } from "@/lib/api"
import { fmtPct, fmtTokens } from "@/lib/format"

export default async function OverviewPage() {
  const [overview, daily, models, sessions] = await Promise.all([
    api.overview().catch(() => null),
    api.daily(30).catch(() => []),
    api.models().catch(() => []),
    api.sessions(10).catch(() => []),
  ])

  const stats = overview ?? {
    total_sessions: 0,
    total_messages: 0,
    input_tokens: 0,
    output_tokens: 0,
    cache_read_tokens: 0,
    total_tokens: 0,
    cache_efficiency_pct: 0,
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Overview</h1>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Total tokens" value={fmtTokens(stats.total_tokens)} />
        <StatCard label="Sessions" value={String(stats.total_sessions)} />
        <StatCard label="Messages" value={String(stats.total_messages)} />
        <StatCard
          label="Cache efficiency"
          value={fmtPct(stats.cache_efficiency_pct)}
          sub="cache reads / (input + cache reads)"
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

      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <h2 className="mb-3 text-sm font-medium text-gray-400">Recent sessions</h2>
        <SessionsTable sessions={sessions} />
      </div>
    </div>
  )
}
