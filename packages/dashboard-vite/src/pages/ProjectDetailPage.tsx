import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"

import { DailyBarChart } from "@/components/charts/DailyBarChart"
import { StatCard } from "@/components/ui/StatCard"
import { api } from "@/lib/api"
import { fmtTokens } from "@/lib/format"
import type { ProjectDetail } from "@/lib/types"

export default function ProjectDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!slug) return
    api
      .project(decodeURIComponent(slug))
      .then(setProject)
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }, [slug])

  if (loading) {
    return <p className="py-8 text-center text-sm text-gray-600">Loading...</p>
  }
  if (notFound || !project) {
    return <p className="py-8 text-center text-sm text-gray-600">Project not found.</p>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">{project.slug}</h1>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Sessions" value={String(project.session_count)} />
        <StatCard label="Input tokens" value={fmtTokens(project.input_tokens)} />
        <StatCard label="Output tokens" value={fmtTokens(project.output_tokens)} />
        <StatCard label="Total tokens" value={fmtTokens(project.total_tokens)} />
      </div>

      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <h2 className="mb-3 text-sm font-medium text-gray-400">Daily breakdown</h2>
        <DailyBarChart data={project.daily} />
      </div>
    </div>
  )
}
