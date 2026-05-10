import { useSearchParams } from "react-router-dom"

const RANGES = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
  { label: "All", days: 0 },
]

export function TimeRangeSelector() {
  const [searchParams, setSearchParams] = useSearchParams()
  const current = parseInt(searchParams.get("days") ?? "30", 10)

  return (
    <div className="flex gap-1">
      {RANGES.map(({ label, days }) => (
        <button
          key={label}
          onClick={() => setSearchParams({ days: String(days) })}
          className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
            current === days
              ? "bg-indigo-600 text-white"
              : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
