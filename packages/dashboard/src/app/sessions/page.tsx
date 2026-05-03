import { SessionsTable } from "@/components/tables/SessionsTable"
import { api } from "@/lib/api"

export default async function SessionsPage() {
  const sessions = await api.sessions(100).catch(() => [])

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Sessions</h1>
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <SessionsTable sessions={sessions} />
      </div>
    </div>
  )
}
