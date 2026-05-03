import { ToolsTable } from "@/components/tables/ToolsTable"
import { api } from "@/lib/api"

export default async function ToolsPage() {
  const tools = await api.tools().catch(() => [])

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Tools</h1>
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <ToolsTable tools={tools} />
      </div>
    </div>
  )
}
