import { notFound } from "next/navigation"

import { ModelBadge } from "@/components/ui/ModelBadge"
import { api } from "@/lib/api"
import { fmtDate, fmtDuration, fmtTokens, truncate } from "@/lib/format"

interface Props {
  params: Promise<{ id: string }>
}

export default async function SessionDetailPage({ params }: Props) {
  const { id } = await params
  const session = await api.session(id).catch(() => null)
  if (!session) notFound()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-mono text-lg font-semibold">{session.id}</h1>
        <p className="text-sm text-gray-500">{session.project_slug}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ["Started", fmtDate(session.started_at)],
          ["Duration", fmtDuration(session.duration_secs)],
          ["Total tokens", fmtTokens(session.total_tokens)],
          ["Messages", String(session.message_count)],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-gray-800 bg-gray-900 px-4 py-3">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="mt-0.5 font-semibold">{value}</p>
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <h2 className="mb-3 text-sm font-medium text-gray-400">Turn-by-turn breakdown</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-left text-xs text-gray-500 uppercase tracking-wider">
                <th className="py-2 pr-4 font-medium">Type</th>
                <th className="py-2 pr-4 font-medium">Model</th>
                <th className="py-2 pr-4 font-medium">Time</th>
                <th className="py-2 pr-4 font-medium text-right">In</th>
                <th className="py-2 pr-4 font-medium text-right">Out</th>
                <th className="py-2 font-medium">Prompt</th>
              </tr>
            </thead>
            <tbody>
              {session.messages.map((m) => (
                <tr key={m.uuid} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                  <td className="py-2 pr-4">
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                        m.record_type === "assistant"
                          ? "bg-indigo-900/60 text-indigo-300"
                          : "bg-gray-800 text-gray-400"
                      }`}
                    >
                      {m.record_type}
                    </span>
                  </td>
                  <td className="py-2 pr-4"><ModelBadge model={m.model} /></td>
                  <td className="py-2 pr-4 text-xs text-gray-500">{fmtDate(m.recorded_at)}</td>
                  <td className="py-2 pr-4 text-right tabular-nums text-xs">
                    {fmtTokens(m.input_tokens)}
                  </td>
                  <td className="py-2 pr-4 text-right tabular-nums text-xs">
                    {fmtTokens(m.output_tokens)}
                  </td>
                  <td className="py-2 max-w-xs text-xs text-gray-500">
                    {m.prompt_text ? truncate(m.prompt_text, 80) : "--"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
