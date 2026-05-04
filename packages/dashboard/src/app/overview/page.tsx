import { Suspense } from "react"

import { DailyBarChart } from "@/components/charts/DailyBarChart"
import { ModelPieChart } from "@/components/charts/ModelPieChart"
import { ProjectsBarChart } from "@/components/charts/ProjectsBarChart"
import { ToolsBarChart } from "@/components/charts/ToolsBarChart"
import { SessionsTable } from "@/components/tables/SessionsTable"
import { CostCard } from "@/components/ui/CostCard"
import { StatCard } from "@/components/ui/StatCard"
import { TimeRangeSelector } from "@/components/ui/TimeRangeSelector"
import { api } from "@/lib/api"
import { fmtPct, fmtTokens } from "@/lib/format"

const VALID_DAYS = [0, 7, 30, 90]

export default async function OverviewPage({
  searchParams,
}: {
  searchParams: Promise<{ days?: string }>
}) {
  const sp = await searchParams
  const raw = parseInt(sp?.days ?? "30", 10)
  const days = VALID_DAYS.includes(raw) ? raw : 30

  // "All" caps the daily chart at 90 bars — rendering years of individual bars is unusable
  const dailyDays = days === 0 ? 90 : days

  const [overview, daily, models, sessions, projects, tools] = await Promise.all([
    api.overview(days).catch(() => null),
    api.daily(dailyDays).catch(() => []),
    api.models(days).catch(() => []),
    api.sessions(10, 0, days).catch(() => []),
    api.projects(days).catch(() => []),
    api.tools(days).catch(() => []),
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
  const chartLabel =
    days === 0 ? "Daily tokens (90 days)" : `Daily tokens (${days} days)`

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Overview</h1>
        <Suspense>
          <TimeRangeSelector />
        </Suspense>
      </div>

      {/* 7 KPI cards */}
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
          cacheCreate5mTokens={s.cache_create_5m_tokens}
          cacheCreate1hTokens={s.cache_create_1h_tokens}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
          <h2 className="mb-3 text-sm font-medium text-gray-400">{chartLabel}</h2>
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
