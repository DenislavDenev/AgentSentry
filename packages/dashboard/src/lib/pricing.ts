export type PricingPlan = "api" | "pro" | "max" | "max20x"

// Per-million-token USD rates for the API plan
export interface ModelRates {
  input: number
  output: number
  cacheRead: number
  cacheCreate5m: number
  cacheCreate1h: number
}

export const MODEL_RATES: Record<string, ModelRates> = {
  "opus": { input: 15, output: 75, cacheRead: 1.5, cacheCreate5m: 18.75, cacheCreate1h: 30 },
  "sonnet": { input: 3, output: 15, cacheRead: 0.3, cacheCreate5m: 3.75, cacheCreate1h: 6 },
  "haiku": { input: 0.8, output: 4, cacheRead: 0.08, cacheCreate5m: 1.0, cacheCreate1h: 1.6 },
}

function getRates(model: string): ModelRates {
  const lower = model.toLowerCase()
  for (const [key, rates] of Object.entries(MODEL_RATES)) {
    if (new RegExp(`\\b${key}\\b|[-_]${key}[-_0-9]|claude-${key}`).test(lower)) return rates
  }
  // Fallback: match by substring for unrecognised variants
  for (const [key, rates] of Object.entries(MODEL_RATES)) {
    if (lower.includes(key)) return rates
  }
  return MODEL_RATES["sonnet"]
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
  cacheCreate5mTokens: number,
  cacheCreate1hTokens: number,
  plan: PricingPlan = "api",
): number {
  if (plan !== "api") return 0
  const r = MODEL_RATES["sonnet"]
  return (
    (inputTokens / 1_000_000) * r.input +
    (outputTokens / 1_000_000) * r.output +
    (cacheReadTokens / 1_000_000) * r.cacheRead +
    (cacheCreate5mTokens / 1_000_000) * r.cacheCreate5m +
    (cacheCreate1hTokens / 1_000_000) * r.cacheCreate1h
  )
}

export function getPlanLabel(plan: PricingPlan): string {
  return {
    api: "API (pay-per-token)",
    pro: "Pro ($20/month)",
    max: "Max ($100/month)",
    max20x: "Max 20x ($200/month)",
  }[plan]
}
