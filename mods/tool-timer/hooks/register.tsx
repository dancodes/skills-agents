import { atom, memberOf, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import { formatDuration } from './format'

const tookMs = atom({ plugin: 'tool-timer', key: 'tookMs' } as const, 0)

export const register: Register = (on, options) => {
  const thresholdMs = Number(options.thresholdSeconds) * 1000

  on('tool.call', async ($, e, next) => {
    const startedAt = await $.clock.now()
    const result = await next(e)
    const ms = (await $.clock.now()) - startedAt

    if (ms > thresholdMs) {
      await update($, memberOf(tookMs, { requestId: e.tool_use_id }), () => ms)
    }

    return result
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'ToolUse' }, async ($, e, next) => {
    const ms = await read($, memberOf(tookMs, e))
    const row = await next(e)

    if (!ms) {
      return row
    }

    const { Box, Text } = $.ui.resolve(e)

    return (
      <Box flexDirection="column">
        {row}
        <Text dimColor>  took {formatDuration(ms)}</Text>
      </Box>
    )
  })
}
