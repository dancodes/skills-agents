import { expect, test } from 'claude-code/testing'

import type { Aside } from '../types'
import { applyLine, hideCommandArgs } from '../hooks/stream'

const start: Aside = { forkId: null, entries: [{ kind: 'question', text: 'why?' }], isBusy: true, isConfirming: false, error: null }

const delta = (text: string) =>
  JSON.stringify({ type: 'stream_event', event: { type: 'content_block_delta', delta: { type: 'text_delta', text } } })

test('builds the chat from the fork stream', async () => {
  const lines = [
    JSON.stringify({ type: 'system', subtype: 'init', session_id: 'fork-1' }),
    delta('Let me '),
    delta('look.'),
    JSON.stringify({ type: 'assistant', message: { content: [{ type: 'tool_use', name: 'Read', input: { file_path: 'a.ts' } }] } }),
    delta('Done.'),
    'not json',
    JSON.stringify({ type: 'result', is_error: false, result: 'Done.' }),
  ]
  const end = lines.reduce(applyLine, start)

  expect(end.forkId).toBe('fork-1')
  expect(end.isBusy).toBe(false)
  expect(end.entries).toEqual([
    { kind: 'question', text: 'why?' },
    { kind: 'answer', text: 'Let me look.' },
    { kind: 'tool', text: 'Read(a.ts)' },
    { kind: 'answer', text: 'Done.' },
  ])
})

test('removes the question from the /aside command row only', async () => {
  const row = '<command-name>/aside</command-name>\n<command-args>secret</command-args>'
  expect(hideCommandArgs(row)).toBe('<command-name>/aside</command-name>\n<command-args></command-args>')
  expect(hideCommandArgs('<command-name>/x</command-name><command-args>a</command-args>')).toContain('>a<')
})
