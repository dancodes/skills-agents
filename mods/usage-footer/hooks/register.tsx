import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Limits } from '../types'
import { contextK, usageParts } from './format'

const limits = atom({ plugin: 'usage-footer', key: 'limits' } as const, [] as Limits)
const tokens = atom({ plugin: 'usage-footer', key: 'tokens' } as const, null as number | null)

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const { rateLimits, context } = await $.session.usage()
    await update($, limits, () => rateLimits)
    await update($, tokens, () => context.tokens ?? null)
    $.clock.every(60_000, () => $.ui.invalidate('ui.render'))

    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    await update($, limits, () => e.rateLimits)
    await update($, tokens, () => e.context.tokens ?? null)

    return next(e)
  })

  on('ui.render', { component: 'PromptHint' }, async ($, e, next) => {
    const parts = usageParts(await read($, limits), await $.clock.now())
    const context = contextK(await read($, tokens))
    const line = await next(e)

    if (!parts.length && !context) {
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
        {context && [<Text dimColor>{parts.length ? ' · ' : '   '}</Text>, <Text color="text">{context}</Text>]}
      </Box>
    )
  })
}
