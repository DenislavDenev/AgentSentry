import { api } from "@/lib/api"
import { fmtDate, truncate } from "@/lib/format"

export default async function PromptsPage() {
  const prompts = await api.prompts(50).catch(() => [])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Prompts</h1>
        <p className="text-sm text-gray-500">Largest user prompts by character count.</p>
      </div>
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        {prompts.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-600">No prompt data yet.</p>
        ) : (
          <div className="space-y-3">
            {prompts.map((p) => (
              <div key={p.uuid} className="rounded border border-gray-800 bg-gray-950 p-3">
                <div className="mb-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
                  <span>{p.project_slug}</span>
                  <span>{fmtDate(p.recorded_at)}</span>
                  <span className="ml-auto tabular-nums">{p.prompt_chars} chars</span>
                </div>
                <p className="whitespace-pre-wrap text-sm text-gray-300">
                  {truncate(p.prompt_text, 400)}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
