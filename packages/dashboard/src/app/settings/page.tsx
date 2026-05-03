"use client"

import { useEffect, useState } from "react"

import { getPlanLabel, MODEL_RATES, type PricingPlan } from "@/lib/pricing"

const PLANS: PricingPlan[] = ["api", "pro", "max", "max20x"]
const STORAGE_KEY = "agentsentry:pricing-plan"

export default function SettingsPage() {
  const [plan, setPlan] = useState<PricingPlan>("api")
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === "api" || stored === "pro" || stored === "max" || stored === "max20x") {
      setPlan(stored)
    }
  }, [])

  function save() {
    localStorage.setItem(STORAGE_KEY, plan)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Settings</h1>

      <div className="max-w-md rounded-lg border border-gray-800 bg-gray-900 p-5">
        <h2 className="mb-1 text-sm font-medium text-gray-300">Pricing plan</h2>
        <p className="mb-4 text-xs text-gray-500">
          Determines how token costs are calculated. Pro/Max plans show token counts only; API
          plan applies per-token rates.
        </p>

        <div className="space-y-2">
          {PLANS.map((p) => (
            <label
              key={p}
              className="flex cursor-pointer items-center gap-3 rounded border border-gray-700 px-4 py-3 hover:border-indigo-700"
            >
              <input
                type="radio"
                name="plan"
                value={p}
                checked={plan === p}
                onChange={() => setPlan(p)}
                className="accent-indigo-500"
              />
              <span className="text-sm text-gray-200">{getPlanLabel(p)}</span>
            </label>
          ))}
        </div>

        <button
          onClick={save}
          className="mt-5 rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
        >
          {saved ? "Saved" : "Save"}
        </button>
      </div>

      <div className="max-w-2xl rounded-lg border border-gray-800 bg-gray-900 p-5">
        <h2 className="mb-1 text-sm font-medium text-gray-300">API pricing reference</h2>
        <p className="mb-4 text-xs text-gray-500">
          Per-million-token USD rates applied when plan is set to API.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-800 text-left text-gray-500 uppercase tracking-wider">
                <th className="py-2 pr-4 font-medium">Model</th>
                <th className="py-2 pr-4 font-medium text-right">Input</th>
                <th className="py-2 pr-4 font-medium text-right">Output</th>
                <th className="py-2 pr-4 font-medium text-right">Cache read</th>
                <th className="py-2 pr-4 font-medium text-right">Cache 5m</th>
                <th className="py-2 font-medium text-right">Cache 1h</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(MODEL_RATES).map(([model, r]) => (
                <tr key={model} className="border-b border-gray-800/50">
                  <td className="py-2 pr-4 font-medium text-gray-300 capitalize">{model}</td>
                  <td className="py-2 pr-4 text-right tabular-nums text-gray-400">${r.input}</td>
                  <td className="py-2 pr-4 text-right tabular-nums text-gray-400">${r.output}</td>
                  <td className="py-2 pr-4 text-right tabular-nums text-gray-400">${r.cacheRead}</td>
                  <td className="py-2 pr-4 text-right tabular-nums text-gray-400">${r.cacheCreate5m}</td>
                  <td className="py-2 text-right tabular-nums text-gray-400">${r.cacheCreate1h}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
