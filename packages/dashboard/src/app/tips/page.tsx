"use client"

import { useEffect, useState } from "react"

import { TipCard } from "@/components/ui/TipCard"
import { api } from "@/lib/api"
import type { OverviewStats, ToolStat } from "@/lib/types"

const DISMISS_KEY = "agentsentry:dismissed-tips"
const DISMISS_DAYS = 14

interface Tip {
  key: string
  title: string
  body: string
  severity: "high" | "medium" | "low"
}

function computeTips(overview: OverviewStats | null, tools: ToolStat[]): Tip[] {
  const tips: Tip[] = []

  if (!overview) {
    tips.push({
      key: "unreachable",
      title: "Watchtower is unreachable",
      body: "Could not fetch data from the Watchtower API. Check that the service is running and NEXT_PUBLIC_API_URL is set correctly.",
      severity: "high",
    })
    return tips
  }

  if (overview.total_sessions === 0) {
    tips.push({
      key: "no-data",
      title: "No data collected yet",
      body: "AgentScout has not ingested any sessions. Verify the AGENT_DATA_DIR mount and that AgentScout is running.",
      severity: "medium",
    })
    return tips
  }

  if (overview.cache_efficiency_pct < 15 && overview.total_tokens > 50_000) {
    tips.push({
      key: "cache-low",
      title: "Low cache efficiency",
      body: `Only ${overview.cache_efficiency_pct.toFixed(1)}% of input tokens were served from cache. Long system prompts and stable context are ideal candidates for prompt caching.`,
      severity: "high",
    })
  } else if (overview.cache_efficiency_pct < 30 && overview.total_tokens > 50_000) {
    tips.push({
      key: "cache-medium",
      title: "Cache efficiency below 30%",
      body: `Cache reads are at ${overview.cache_efficiency_pct.toFixed(1)}%. Consider pinning stable context blocks to improve the cache hit rate.`,
      severity: "medium",
    })
  }

  const totalResultTokens = tools.reduce((s, t) => s + t.result_tokens, 0)
  const resultRatio = overview.total_tokens > 0 ? totalResultTokens / overview.total_tokens : 0
  if (resultRatio > 0.4) {
    tips.push({
      key: "tool-tokens",
      title: "Tool results are consuming >40% of tokens",
      body: "Large tool outputs (file reads, bash output) are inflating context. Consider limiting Read output with line ranges, or filtering verbose Bash results.",
      severity: "medium",
    })
  }

  for (const t of tools.filter((t) => t.error_rate_pct > 15 && t.invocation_count >= 5)) {
    tips.push({
      key: `err-${t.tool_name}`,
      title: `High error rate on ${t.tool_name}`,
      body: `${t.tool_name} is failing ${t.error_rate_pct.toFixed(1)}% of the time. Review error patterns to reduce wasted token spend on retries.`,
      severity: "medium",
    })
  }

  if (tips.length === 0) {
    tips.push({
      key: "healthy",
      title: "Everything looks healthy",
      body: "No significant inefficiencies detected. Keep an eye on cache efficiency as your usage grows.",
      severity: "low",
    })
  }

  return tips
}

function loadDismissed(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(DISMISS_KEY) ?? "{}")
  } catch {
    return {}
  }
}

function saveDismissed(record: Record<string, number>) {
  localStorage.setItem(DISMISS_KEY, JSON.stringify(record))
}

export default function TipsPage() {
  const [tips, setTips] = useState<Tip[]>([])
  const [dismissed, setDismissed] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setDismissed(loadDismissed())
    Promise.all([api.overview().catch(() => null), api.tools().catch(() => [])]).then(
      ([overview, tools]) => {
        setTips(computeTips(overview, tools))
        setLoading(false)
      },
    )
  }, [])

  function dismiss(key: string) {
    const next = { ...dismissed, [key]: Date.now() }
    setDismissed(next)
    saveDismissed(next)
  }

  const cutoff = Date.now() - DISMISS_DAYS * 24 * 60 * 60 * 1000
  const visible = tips.filter((t) => !dismissed[t.key] || dismissed[t.key] < cutoff)

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Tips</h1>
        <p className="text-sm text-gray-500">
          Rule-based optimization suggestions. Dismissed tips reappear after {DISMISS_DAYS} days.
        </p>
      </div>
      {loading ? (
        <p className="text-sm text-gray-600">Loading...</p>
      ) : visible.length === 0 ? (
        <p className="text-sm text-gray-500">No suggestions right now. Check back after more activity.</p>
      ) : (
        <div className="space-y-3">
          {visible.map(({ key, ...rest }) => (
            <TipCard key={key} {...rest} onDismiss={() => dismiss(key)} />
          ))}
        </div>
      )}
    </div>
  )
}
