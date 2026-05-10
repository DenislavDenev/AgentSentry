import { useEffect, useState } from "react"

import { StatCard } from "@/components/ui/StatCard"
import { fmtCost } from "@/lib/format"
import { calcCostGeneric, type PricingPlan } from "@/lib/pricing"

interface Props {
  inputTokens: number
  outputTokens: number
  cacheReadTokens: number
  cacheCreate5mTokens: number
  cacheCreate1hTokens: number
}

const STORAGE_KEY = "agentsentry:pricing-plan"

function readPlan(): PricingPlan {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === "api" || v === "pro" || v === "max" || v === "max20x") return v
  } catch {}
  return "api"
}

export function CostCard({
  inputTokens,
  outputTokens,
  cacheReadTokens,
  cacheCreate5mTokens,
  cacheCreate1hTokens,
}: Props) {
  const [plan, setPlan] = useState<PricingPlan>("api")

  useEffect(() => {
    setPlan(readPlan())
    const handler = () => setPlan(readPlan())
    window.addEventListener("storage", handler)
    return () => window.removeEventListener("storage", handler)
  }, [])

  const cost = calcCostGeneric(
    inputTokens,
    outputTokens,
    cacheReadTokens,
    cacheCreate5mTokens,
    cacheCreate1hTokens,
    plan,
  )
  const value = plan === "api" ? fmtCost(cost) : "N/A"
  const sub = plan === "api" ? "API rates · Sonnet avg" : "Subscription plan"

  return <StatCard label="Est. cost" value={value} sub={sub} />
}
