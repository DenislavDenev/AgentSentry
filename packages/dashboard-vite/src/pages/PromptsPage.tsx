import { useEffect, useState } from "react"

import { PromptDrawer } from "@/components/ui/PromptDrawer"
import { fmtDate, fmtTokens } from "@/lib/format"
import type { PromptStat } from "@/lib/types"

type SortMode = "tokens" | "recent"

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<PromptStat[]>([])
  const [loading, setLoading] = useState(true)
  const [sort, setSort] = useState<SortMode>("tokens")
  const [selected, setSelected] = useState<PromptStat | null>(null)

  useEffect(() => {
    fetch("/api/prompts?limit=50", { cache: "no-store" })
      .then((r) => r.json())
      .then((data: PromptStat[]) => setPrompts(data))
      .catch(() => setPrompts([]))
      .finally(() => setLoading(false))
  }, [])

  const sorted = [...prompts].sort((a, b) =>
    sort === "tokens"
      ? b.billable_tokens - a.billable_tokens
      : new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime(),
  )

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Prompts</h1>
        <p className="text-sm text-gray-500">
          Largest prompts ranked by the assistant response they triggered.
        </p>
      </div>

      <div className="flex items-center gap-2">
        {(["tokens", "recent"] as SortMode[]).map((mode) => (
          <button
            key={mode}
            onClick={() => setSort(mode)}
            className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
              sort === mode
                ? "bg-indigo-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-gray-200"
            }`}
          >
            {mode === "tokens" ? "Most tokens" : "Most recent"}
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        {loading ? (
          <p className="py-8 text-center text-sm text-gray-600">Loading...</p>
        ) : sorted.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-600">No prompt data yet.</p>
        ) : (
          <div className="space-y-3">
            {sorted.map((p) => (
              <button
                key={p.uuid}
                onClick={() => setSelected(p)}
                className="w-full text-left rounded border border-gray-800 bg-gray-950 p-3 hover:border-indigo-700 transition-colors"
              >
                <div className="mb-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
                  <span className="truncate max-w-xs">{p.project_slug}</span>
                  <span>{fmtDate(p.recorded_at)}</span>
                  <span className="ml-auto tabular-nums text-indigo-400">
                    {fmtTokens(p.billable_tokens)} billable
                  </span>
                  <span className="tabular-nums">{p.prompt_chars} chars</span>
                </div>
                <p className="sensitive whitespace-pre-wrap text-sm text-gray-300 line-clamp-3">
                  {p.prompt_text.slice(0, 400)}
                  {p.prompt_text.length > 400 ? "..." : ""}
                </p>
              </button>
            ))}
          </div>
        )}
      </div>

      <PromptDrawer prompt={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
