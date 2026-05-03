"use client"

import { useEffect, useRef } from "react"

import type { ToolStat } from "@/lib/types"

interface Props {
  data: ToolStat[]
  height?: number
}

export function ToolsBarChart({ data, height = 260 }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  // Sort descending, take top 10, reverse so ECharts renders highest at top
  // (ECharts horizontal bar draws Y categories bottom→top).
  const top10 = [...data]
    .sort((a, b) => b.invocation_count - a.invocation_count)
    .slice(0, 10)
    .reverse()

  useEffect(() => {
    if (!ref.current || top10.length === 0) return

    let chart: import("echarts").ECharts | null = null

    import("echarts").then((echarts) => {
      if (!ref.current) return
      chart = echarts.init(ref.current, "dark")
      chart.setOption({
        backgroundColor: "transparent",
        tooltip: { trigger: "axis" },
        grid: { top: 8, bottom: 8, left: 80, right: 48, containLabel: false },
        xAxis: {
          type: "value",
          axisLabel: { color: "#6b7280", fontSize: 10 },
          splitLine: { lineStyle: { color: "#1f2937" } },
        },
        yAxis: {
          type: "category",
          data: top10.map((t) => t.tool_name),
          axisLabel: { color: "#9ca3af", fontSize: 11 },
          axisLine: { lineStyle: { color: "#374151" } },
        },
        series: [
          {
            type: "bar",
            data: top10.map((t) => t.invocation_count),
            itemStyle: { color: "#06b6d4", borderRadius: [0, 4, 4, 0] },
            label: {
              show: true,
              position: "right",
              color: "#6b7280",
              fontSize: 10,
            },
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
  }, [top10])

  if (top10.length === 0) {
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
