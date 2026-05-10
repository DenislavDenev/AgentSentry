import { useEffect, useState } from "react"

import { SessionsTable } from "@/components/tables/SessionsTable"
import { api } from "@/lib/api"
import type { SessionSummary } from "@/lib/types"

export default function SessionsPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.sessions(100).catch(() => []).then(setSessions).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Sessions</h1>
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        {loading ? (
          <p className="py-8 text-center text-sm text-gray-600">Loading...</p>
        ) : (
          <SessionsTable sessions={sessions} />
        )}
      </div>
    </div>
  )
}
