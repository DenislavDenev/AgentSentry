import { notFound } from "next/navigation"

import { DailyBarChart } from "@/components/charts/DailyBarChart"
import { StatCard } from "@/components/ui/StatCard"
import { api } from "@/lib/api"
import { fmtTokens } from "@/lib/format"

interface Props {
  params: Promise<{ slug: string }>
}

export default async function ProjectDetailPage({ params }: Props) {
  const { slug } = await params
  const project = await api.project(decodeURIComponent(slug)).catch(() => null)
  if (!project) notFound()

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
