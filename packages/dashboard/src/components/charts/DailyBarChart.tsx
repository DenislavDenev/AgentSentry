"use client"

import { useEffect, useRef } from "react"

import type { DailyStats } from "@/lib/types"

interface Props {
  data: DailyStats[]
  height?: number
}

export function DailyBarChart({ data, height = 280 }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current || data.length === 0) return

    let chart: import("echarts").ECharts | null = null

    import("echarts").then((echarts) => {
      if (!ref.current) return
      chart = echarts.init(ref.current, "dark")
      chart.setOption({
        backgroundColor: "transparent",
        tooltip: { trigger: "axis" },
        legend: {
          data: ["Input", "Output", "Cache read"],
          textStyle: { color: "#9ca3af" },
          bottom: 0,
        },
        grid: { top: 16, bottom: 48, left: 48, right: 16 },
        xAxis: {
          type: "category",
          data: data.map((d) => d.date),
          axisLabel: { color: "#6b7280", fontSize: 11 },
          axisLine: { lineStyle: { color: "#374151" } },
        },
        yAxis: {
          type: "value",
          axisLabel: {
            color: "#6b7280",
            fontSize: 11,
            formatter: (v: number) => (v >= 1000 ? `${(v / 1000).toFixed(0)}K` : String(v)),
          },
          splitLine: { lineStyle: { color: "#1f2937" } },
        },
        series: [
          {
            name: "Input",
            type: "bar",
            stack: "tokens",
            data: data.map((d) => d.input_tokens),
            itemStyle: { color: "#6366f1" },
          },
          {
            name: "Output",
            type: "bar",
            stack: "tokens",
            data: data.map((d) => d.output_tokens),
            itemStyle: { color: "#8b5cf6" },
          },
          {
            name: "Cache read",
            type: "bar",
            stack: "tokens",
            data: data.map((d) => d.cache_read_tokens),
            itemStyle: { color: "#06b6d4" },
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
  }, [data])

  if (data.length === 0) {
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
