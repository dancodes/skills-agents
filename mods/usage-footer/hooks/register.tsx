import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Limits } from '../types'
import { usageParts } from './format'

const limits = atom({ plugin: 'usage-footer', key: 'limits' } as const, [] as Limits)

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const { rateLimits } = await $.session.usage()
    await update($, limits, () => rateLimits)
    $.clock.every(60_000, () => $.ui.invalidate('ui.render'))

    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    await update($, limits, () => e.rateLimits)

    return next(e)
  })

  on('ui.render', { component: 'PromptHint' }, async ($, e, next) => {
    const parts = usageParts(await read($, limits), await $.clock.now())
    const line = await next(e)

    if (!parts.length) {
      return line
    }

    const { Box, Text } = $.ui.resolve(e)

    return (
      <Box flexDirection="row">
        {line}
        {parts.flatMap((part, index) => [
          <Text dimColor>{index ? ' · ' : '   '}</Text>,
          <Text color="text">{part.percent}</Text>,
          <Text dimColor> {part.label}</Text>,
          ...(part.reset
            ? [<Text dimColor> (</Text>, <Text color="warning">{part.reset}</Text>, <Text dimColor>)</Text>]
            : []),
        ])}
      </Box>
    )
  })
}
