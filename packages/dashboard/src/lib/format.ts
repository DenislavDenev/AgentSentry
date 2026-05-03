export function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

export function fmtCost(usd: number): string {
  if (usd === 0) return "--"
  if (usd >= 1) return `$${usd.toFixed(2)}`
  return `$${usd.toFixed(4)}`
}

export function fmtDuration(secs: number | null): string {
  if (secs === null || secs < 0) return "--"
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "--"
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  })
}

export function fmtPct(n: number): string {
  return `${n.toFixed(1)}%`
}

export function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + "..." : s
}
