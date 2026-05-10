import { useEffect, useState } from "react"

import { ToolsTable } from "@/components/tables/ToolsTable"
import { api } from "@/lib/api"
import type { ToolStat } from "@/lib/types"

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolStat[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.tools().catch(() => []).then(setTools).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Tools</h1>
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        {loading ? (
          <p className="py-8 text-center text-sm text-gray-600">Loading...</p>
        ) : (
          <ToolsTable tools={tools} />
        )}
      </div>
    </div>
  )
}
