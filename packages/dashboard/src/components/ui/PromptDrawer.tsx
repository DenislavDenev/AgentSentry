"use client"

import type { PromptStat } from "@/lib/types"
import { fmtDate, fmtTokens } from "@/lib/format"

interface Props {
  prompt: PromptStat | null
  onClose: () => void
}

export function PromptDrawer({ prompt, onClose }: Props) {
  if (!prompt) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Panel */}
      <div className="fixed right-0 top-0 z-50 flex h-full w-full max-w-xl flex-col bg-gray-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-800 px-5 py-4">
          <h2 className="text-sm font-semibold text-gray-200">Prompt detail</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            {[
              ["Session", prompt.session_id.slice(0, 8) + "..."],
              ["Project", prompt.project_slug],
              ["Date", fmtDate(prompt.recorded_at)],
              ["Tokens", fmtTokens(prompt.input_tokens)],
              ["Characters", String(prompt.prompt_chars)],
            ].map(([label, value]) => (
              <div key={label} className="rounded border border-gray-800 bg-gray-950 px-3 py-2">
                <p className="text-xs text-gray-500">{label}</p>
                <p className="mt-0.5 text-sm text-gray-200 break-all">{value}</p>
              </div>
            ))}
          </div>

          <div>
            <p className="mb-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Full prompt text
            </p>
            <pre className="sensitive whitespace-pre-wrap rounded border border-gray-800 bg-gray-950 p-3 text-xs text-gray-300 leading-relaxed">
              {prompt.prompt_text}
            </pre>
          </div>
        </div>
      </div>
    </>
  )
}
