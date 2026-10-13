export const formatDuration = (ms: number) => {
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)}s`

  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}
