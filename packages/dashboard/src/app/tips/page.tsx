import { TipCard } from "@/components/ui/TipCard"
import { api } from "@/lib/api"

interface Tip {
  title: string
  body: string
  severity: "high" | "medium" | "low"
}

function computeTips(
  overview: Awaited<ReturnType<typeof api.overview>> | null,
  tools: Awaited<ReturnType<typeof api.tools>>,
): Tip[] {
  const tips: Tip[] = []

  if (!overview) {
    tips.push({
      title: "Watchtower is unreachable",
      body: "Could not fetch data from the Watchtower API. Check that the service is running and NEXT_PUBLIC_API_URL is set correctly.",
      severity: "high",
    })
    return tips
  }

  if (overview.total_sessions === 0) {
    tips.push({
      title: "No data collected yet",
      body: "AgentScout has not ingested any sessions. Verify the AGENT_DATA_DIR mount and that AgentScout is running.",
      severity: "medium",
    })
    return tips
  }

  // Cache efficiency
  if (overview.cache_efficiency_pct < 15 && overview.total_tokens > 50_000) {
    tips.push({
      title: "Low cache efficiency",
      body: `Only ${overview.cache_efficiency_pct.toFixed(1)}% of input tokens were served from cache. Long system prompts and stable context are ideal candidates for prompt caching.`,
      severity: "high",
    })
  } else if (overview.cache_efficiency_pct < 30 && overview.total_tokens > 50_000) {
    tips.push({
      title: "Cache efficiency below 30%",
      body: `Cache reads are at ${overview.cache_efficiency_pct.toFixed(1)}%. Consider pinning stable context blocks to improve the cache hit rate.`,
      severity: "medium",
    })
  }

  // High tool result token cost
  const totalResultTokens = tools.reduce((s, t) => s + t.result_tokens, 0)
  const resultRatio = overview.total_tokens > 0 ? totalResultTokens / overview.total_tokens : 0
  if (resultRatio > 0.4) {
    tips.push({
      title: "Tool results are consuming >40% of tokens",
      body: "Large tool outputs (file reads, bash output) are inflating context. Consider limiting Read output with line ranges, or filtering verbose Bash results.",
      severity: "medium",
    })
  }

  // High error rate tools
  const erroneousTools = tools.filter((t) => t.error_rate_pct > 15 && t.invocation_count >= 5)
  for (const t of erroneousTools) {
    tips.push({
      title: `High error rate on ${t.tool_name}`,
      body: `${t.tool_name} is failing ${t.error_rate_pct.toFixed(1)}% of the time. Review error patterns to reduce wasted token spend on retries.`,
      severity: "medium",
    })
  }

  if (tips.length === 0) {
    tips.push({
      title: "Everything looks healthy",
      body: "No significant inefficiencies detected. Keep an eye on cache efficiency as your usage grows.",
      severity: "low",
    })
  }

  return tips
}

export default async function TipsPage() {
  const [overview, tools] = await Promise.all([
    api.overview().catch(() => null),
    api.tools().catch(() => []),
  ])

  const tips = computeTips(overview, tools)

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Tips</h1>
        <p className="text-sm text-gray-500">Rule-based optimization suggestions.</p>
      </div>
      <div className="space-y-3">
        {tips.map((tip, i) => (
          <TipCard key={i} {...tip} />
        ))}
      </div>
    </div>
  )
}
