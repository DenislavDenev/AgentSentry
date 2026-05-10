interface Props {
  model: string | null
}

function getModelStyle(model: string): { label: string; className: string } {
  const lower = model.toLowerCase()
  if (lower.includes("opus")) return { label: model, className: "bg-purple-900/60 text-purple-300" }
  if (lower.includes("sonnet")) return { label: model, className: "bg-blue-900/60 text-blue-300" }
  if (lower.includes("haiku")) return { label: model, className: "bg-green-900/60 text-green-300" }
  return { label: model, className: "bg-gray-800 text-gray-400" }
}

export function ModelBadge({ model }: Props) {
  if (!model) return <span className="text-gray-600">--</span>
  const { label, className } = getModelStyle(model)
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${className}`}>
      {label}
    </span>
  )
}
