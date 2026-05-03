type Severity = "high" | "medium" | "low"

interface TipCardProps {
  title: string
  body: string
  severity: Severity
}

const SEVERITY_STYLES: Record<Severity, string> = {
  high: "border-red-700 bg-red-950/40",
  medium: "border-yellow-700 bg-yellow-950/30",
  low: "border-gray-700 bg-gray-900",
}

const BADGE_STYLES: Record<Severity, string> = {
  high: "bg-red-800 text-red-200",
  medium: "bg-yellow-800 text-yellow-200",
  low: "bg-gray-700 text-gray-300",
}

export function TipCard({ title, body, severity }: TipCardProps) {
  return (
    <div className={`rounded-lg border px-5 py-4 ${SEVERITY_STYLES[severity]}`}>
      <div className="flex items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${BADGE_STYLES[severity]}`}>
          {severity.toUpperCase()}
        </span>
        <p className="text-sm font-semibold text-gray-100">{title}</p>
      </div>
      <p className="mt-2 text-sm text-gray-400">{body}</p>
    </div>
  )
}
