import { fmtPct, fmtTokens } from "@/lib/format"
import type { ToolStat } from "@/lib/types"

interface Props {
  tools: ToolStat[]
}

export function ToolsTable({ tools }: Props) {
  if (tools.length === 0) {
    return <p className="py-8 text-center text-sm text-gray-600">No tool data yet.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-left text-xs text-gray-500 uppercase tracking-wider">
            <th className="py-2 pr-4 font-medium">Tool</th>
            <th className="py-2 pr-4 font-medium text-right">Calls</th>
            <th className="py-2 pr-4 font-medium text-right">Result tokens</th>
            <th className="py-2 pr-4 font-medium text-right">Errors</th>
            <th className="py-2 font-medium text-right">Error rate</th>
          </tr>
        </thead>
        <tbody>
          {tools.map((t) => (
            <tr key={t.tool_name} className="border-b border-gray-800/50 hover:bg-gray-900/50">
              <td className="py-2 pr-4 font-mono text-xs text-gray-200">{t.tool_name}</td>
              <td className="py-2 pr-4 text-right tabular-nums">{t.invocation_count}</td>
              <td className="py-2 pr-4 text-right tabular-nums text-gray-400">
                {fmtTokens(t.result_tokens)}
              </td>
              <td className="py-2 pr-4 text-right tabular-nums text-gray-400">{t.error_count}</td>
              <td
                className={`py-2 text-right tabular-nums ${
                  t.error_rate_pct > 10 ? "text-red-400" : "text-gray-400"
                }`}
              >
                {fmtPct(t.error_rate_pct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
