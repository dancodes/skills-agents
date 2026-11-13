import { expect, mock, test } from 'claude-code/testing'
import type { Engine, On } from 'claude-code'

import { formatDuration } from '../hooks/format'

const runFor = async ($: Engine, on: On, ms: number) => {
  const clock = mock.clock(on)
  let id = ''
  on('tool.call', async ($, e) => {
    id = e.tool_use_id
    await clock.sleep(ms)
    return { result: { stdout: '', stderr: '', interrupted: false } }
  })
  on('ui.render', { component: 'ToolUse' }, ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>Bash(make)</Text>
  })

  const call = $.tool.call({ tool: 'Bash', command: 'make' })
  await clock.advance(ms)
  await call

  const props = { tool_use_id: id, tool: 'Bash', input: { command: 'make' }, isRunning: false, isErrored: false, isInterrupted: false }
  const ui = await $.ui.mount({ plugin: 'tool-timer', surface: 'terminal', component: 'ToolUse', requestId: id, props })
  return (await ui.find({ type: 'Text', text: /took/ }))?.text
}

test('shows the duration of a call slower than the threshold', async ($, on) => {
  expect(await runFor($, on, 6200)).toBe('  took 6.2s')
})

test('hides the duration of a call under the threshold', async ($, on) => {
  expect(await runFor($, on, 4000)).toBeUndefined()
})

test('reads the threshold from the thresholdSeconds option', { options: { thresholdSeconds: 10 } }, async ($, on) => {
  expect(await runFor($, on, 6200)).toBeUndefined()
})

test('formats seconds and minutes', async () => {
  expect(formatDuration(5300)).toBe('5.3s')
  expect(formatDuration(64_000)).toBe('1m 4s')
})
