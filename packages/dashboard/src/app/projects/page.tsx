import Link from "next/link"

import { api } from "@/lib/api"
import { fmtTokens } from "@/lib/format"

export default async function ProjectsPage() {
  const projects = await api.projects().catch(() => [])

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Projects</h1>
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        {projects.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-600">No projects yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left text-xs text-gray-500 uppercase tracking-wider">
                  <th className="py-2 pr-4 font-medium">Project</th>
                  <th className="py-2 pr-4 font-medium text-right">Sessions</th>
                  <th className="py-2 pr-4 font-medium text-right">Input</th>
                  <th className="py-2 pr-4 font-medium text-right">Output</th>
                  <th className="py-2 font-medium text-right">Total</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((p) => (
                  <tr key={p.slug} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                    <td className="py-2 pr-4">
                      <Link
                        href={`/projects/${encodeURIComponent(p.slug)}`}
                        className="text-indigo-400 hover:text-indigo-300"
                      >
                        {p.slug}
                      </Link>
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums text-gray-400">
                      {p.session_count}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {fmtTokens(p.input_tokens)}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {fmtTokens(p.output_tokens)}
                    </td>
                    <td className="py-2 text-right tabular-nums font-medium">
                      {fmtTokens(p.total_tokens)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
