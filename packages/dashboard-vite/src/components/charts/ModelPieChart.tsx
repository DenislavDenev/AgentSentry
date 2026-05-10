import { useEffect, useRef } from "react"

import type { ModelStat } from "@/lib/types"

interface Props {
  data: ModelStat[]
  height?: number
}

const COLORS = ["#6366f1", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444"]

export function ModelPieChart({ data, height = 280 }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current || data.length === 0) return

    let chart: import("echarts").ECharts | null = null

    import("echarts").then((echarts) => {
      if (!ref.current) return
      chart = echarts.init(ref.current, "dark")
      chart.setOption({
        backgroundColor: "transparent",
        tooltip: {
          trigger: "item",
          formatter: "{b}: {d}%",
        },
        legend: {
          orient: "vertical",
          right: 8,
          top: "center",
          textStyle: { color: "#9ca3af", fontSize: 11 },
        },
        series: [
          {
            type: "pie",
            radius: ["40%", "70%"],
            center: ["38%", "50%"],
            data: data.map((d, i) => ({
              name: d.model,
              value: d.total_tokens,
              itemStyle: { color: COLORS[i % COLORS.length] },
            })),
            label: { show: false },
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
