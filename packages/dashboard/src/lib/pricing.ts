export type PricingPlan = "api" | "pro" | "max"

// Per-million-token USD rates for API plan
const MODEL_RATES: Record<string, { input: number; output: number; cacheRead: number }> = {
  "claude-opus": { input: 15, output: 75, cacheRead: 1.5 },
  "claude-sonnet": { input: 3, output: 15, cacheRead: 0.3 },
  "claude-haiku": { input: 0.8, output: 4, cacheRead: 0.08 },
}

function getRates(model: string) {
  for (const [key, rates] of Object.entries(MODEL_RATES)) {
    if (model.toLowerCase().includes(key)) return rates
  }
  return MODEL_RATES["claude-sonnet"]
}

export function calcCost(
  model: string,
  inputTokens: number,
  outputTokens: number,
  cacheReadTokens: number,
  plan: PricingPlan = "api",
): number {
  if (plan !== "api") return 0
  const r = getRates(model)
  return (
    (inputTokens / 1_000_000) * r.input +
    (outputTokens / 1_000_000) * r.output +
    (cacheReadTokens / 1_000_000) * r.cacheRead
  )
}

export function calcCostGeneric(
  inputTokens: number,
  outputTokens: number,
  cacheReadTokens: number,
  plan: PricingPlan = "api",
): number {
  if (plan !== "api") return 0
  const r = MODEL_RATES["claude-sonnet"]
  return (
    (inputTokens / 1_000_000) * r.input +
    (outputTokens / 1_000_000) * r.output +
    (cacheReadTokens / 1_000_000) * r.cacheRead
  )
}

export function getPlanLabel(plan: PricingPlan): string {
  return { api: "API (pay-per-token)", pro: "Pro (subscription)", max: "Max (subscription)" }[plan]
}
