import { useEffect, useState } from "react"
import { Link } from "react-router-dom"

import { api } from "@/lib/api"
import { fmtTokens } from "@/lib/format"
import type { ProjectSummary } from "@/lib/types"

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.projects().catch(() => []).then(setProjects).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Projects</h1>
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        {loading ? (
          <p className="py-8 text-center text-sm text-gray-600">Loading...</p>
        ) : projects.length === 0 ? (
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
                        to={`/projects/${encodeURIComponent(p.slug)}`}
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
