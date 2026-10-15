import type { Limits } from '../types'

export type UsagePart = { label: string; percent: string; reset: string | null }

const LABELS: Record<string, string> = { five_hour: '5h', seven_day: 'wk' }

const timeLeft = (ms: number) => {
  const minutes = Math.max(0, Math.round(ms / 60_000))
  const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60)

  if (days) return `${days}d${hours}h`
  return hours ? `${hours}h${minutes % 60}m` : `${minutes}m`
}

export const usageParts = (limits: Limits, now: number): UsagePart[] =>
  limits.flatMap(limit => {
    const label = LABELS[limit.kind]
    if (!label) return []

    const reset = limit.resetsAt ? timeLeft(Date.parse(limit.resetsAt) - now) : null
    return [{ label, percent: `${limit.percentUsed}%`, reset }]
  })

export const contextK = (tokens: number | null | undefined) => (tokens == null ? null : `${Math.round(tokens / 1000)}k`)
