import { useEffect, useRef } from "react"

import type { ProjectSummary } from "@/lib/types"

interface Props {
  data: ProjectSummary[]
  height?: number
}

// Shorten the long Claude Code project slugs for display
function shortSlug(slug: string): string {
  const parts = slug.split("--")
  const last = parts[parts.length - 1]
  if (last && last.length > 4) return last.replace(/-[a-f0-9]{6,}$/, "")
  return slug.slice(-30)
}

export function ProjectsBarChart({ data, height = 280 }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  // Sort descending by total tokens, take top 8, then REVERSE so ECharts
  // horizontal bar renders highest at the top (ECharts draws Y categories bottom to top).
  const top8 = [...data]
    .sort((a, b) => b.total_tokens - a.total_tokens)
    .slice(0, 8)
    .reverse()

  useEffect(() => {
    if (!ref.current || top8.length === 0) return

    let chart: import("echarts").ECharts | null = null

    import("echarts").then((echarts) => {
      if (!ref.current) return
      chart = echarts.init(ref.current, "dark")
      chart.setOption({
        backgroundColor: "transparent",
        tooltip: { trigger: "axis" },
        legend: {
          data: ["Input", "Output"],
          textStyle: { color: "#9ca3af" },
          bottom: 0,
        },
        grid: { top: 16, bottom: 48, left: 110, right: 16 },
        xAxis: {
          type: "value",
          axisLabel: {
            color: "#6b7280",
            fontSize: 10,
            formatter: (v: number) =>
              v >= 1_000_000
                ? `${(v / 1_000_000).toFixed(1)}M`
                : v >= 1000
                  ? `${(v / 1000).toFixed(0)}K`
                  : String(v),
          },
          splitLine: { lineStyle: { color: "#1f2937" } },
        },
        yAxis: {
          type: "category",
          data: top8.map((p) => shortSlug(p.slug)),
          axisLabel: { color: "#9ca3af", fontSize: 10 },
          axisLine: { lineStyle: { color: "#374151" } },
        },
        series: [
          {
            name: "Input",
            type: "bar",
            data: top8.map((p) => p.input_tokens),
            itemStyle: { color: "#38bdf8" },
          },
          {
            name: "Output",
            type: "bar",
            data: top8.map((p) => p.output_tokens),
            itemStyle: { color: "#818cf8" },
          },
        ],
      })
    })

    const observer = new ResizeObserver(() => chart?.resize())
    observer.observe(ref.current)

    return () => {
      observer.disconnect()
      chart?.dispose()
    }
  }, [top8])

  if (top8.length === 0) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center text-sm text-gray-600"
      >
        No data
      </div>
    )
  }

  return <div ref={ref} style={{ height, width: "100%" }} />
}
