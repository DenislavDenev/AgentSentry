import { Link } from "react-router-dom"

import { fmtDate, fmtDuration, fmtTokens } from "@/lib/format"
import type { SessionSummary } from "@/lib/types"

interface Props {
  sessions: SessionSummary[]
}

export function SessionsTable({ sessions }: Props) {
  if (sessions.length === 0) {
    return <p className="py-8 text-center text-sm text-gray-600">No sessions yet.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-left text-xs text-gray-500 uppercase tracking-wider">
            <th className="py-2 pr-4 font-medium">Session</th>
            <th className="py-2 pr-4 font-medium">Project</th>
            <th className="py-2 pr-4 font-medium">Started</th>
            <th className="py-2 pr-4 font-medium">Duration</th>
            <th className="py-2 pr-4 font-medium text-right">Tokens</th>
            <th className="py-2 font-medium text-right">Messages</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
              <td className="py-2 pr-4">
                <Link
                  to={`/sessions/${s.id}`}
                  className="font-mono text-xs text-indigo-400 hover:text-indigo-300"
                >
                  {s.id.slice(0, 8)}
                </Link>
              </td>
              <td className="py-2 pr-4 text-gray-400 text-xs">{s.project_slug}</td>
              <td className="py-2 pr-4 text-gray-400">{fmtDate(s.started_at)}</td>
              <td className="py-2 pr-4 text-gray-400">{fmtDuration(s.duration_secs)}</td>
              <td className="py-2 pr-4 text-right tabular-nums">{fmtTokens(s.total_tokens)}</td>
              <td className="py-2 text-right tabular-nums text-gray-400">{s.message_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
