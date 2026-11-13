import { atom, read, update } from 'claude-code'
import type { Engine, Register } from 'claude-code'

import type { Aside } from '../types'
import { applyLine, hideCommandArgs } from './stream'

const PANE = 'aside'
const TOOLS = 'Read,Grep,Glob,WebSearch,WebFetch'
const EMPTY: Aside = { forkId: null, entries: [], isBusy: false, isConfirming: false, error: null }
const aside = atom({ plugin: 'aside', key: 'aside' } as const, EMPTY)

let running: AsyncGenerator | undefined

const ask = async ($: Engine, question: string) => {
  const current = await read($, aside)
  if (current.isBusy) {
    return
  }
  await update($, aside, a => ({ ...a, isBusy: true, error: null, entries: [...a.entries, { kind: 'question', text: question }] }))

  const resumeId = current.forkId ?? (await $.session.id())
  const argv = [
    'claude', '-p', '--resume', resumeId, ...(current.forkId ? [] : ['--fork-session']),
    '--model', await $.session.model(),
    '--output-format', 'stream-json', '--verbose', '--include-partial-messages',
    `--tools=${TOOLS}`, `--allowedTools=${TOOLS}`, '--strict-mcp-config',
  ]
  const child = $.process.spawn({ argv, input: question })
  running = child
  let pending = ''
  let stderr = ''
  try {
    for await (const { stream, text } of child) {
      if (stream === 'stderr') {
        stderr += text
        continue
      }
      const lines = (pending + text).split('\n')
      pending = lines.pop() ?? ''
      for (const line of lines) {
        await update($, aside, a => applyLine(a, line))
      }
    }
  } catch (err) {
    stderr += String(err)
  } finally {
    if (running === child) {
      running = undefined
      await update($, aside, a => (a.isBusy ? { ...a, isBusy: false, error: stderr.trim() || 'The fork stopped.' } : a))
    }
  }
}

const discard = async ($: Engine) => {
  const { forkId } = await read($, aside)
  await running?.return(undefined)
  running = undefined
  await update($, aside, () => EMPTY)
  await $.ui.close({ id: PANE })
  if (forkId) {
    const config = (await $.env.get('CLAUDE_CONFIG_DIR')) ?? `${await $.env.get('HOME')}/.claude`
    await $.process.run(['find', `${config}/projects`, '-maxdepth', '2', '-name', `${forkId}.jsonl`, '-delete'])
  }
}

const promote = async ($: Engine) => {
  const { forkId } = await read($, aside)
  if (!forkId) {
    return
  }
  await update($, aside, () => EMPTY)
  await $.ui.close({ id: PANE })
  try {
    await $.command.run({ command: 'resume', args: forkId })
  } catch {
    await $.prompt.fill({ text: `/resume ${forkId}` })
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'aside',
      description: 'Ask a side question in a fork of this session',
      argumentHint: '[question]',
      immediate: true,
    })
    return next(e)
  })

  on('command.run', { command: 'aside' }, async ($, e) => {
    await $.ui.open({ id: PANE, title: 'aside', focus: true, closeOnEscape: true })
    const question = e.args.trim()
    if (question) {
      void ask($, question)
    }
    return {}
  })

  on('session.append', async ($, e, next) => {
    if (e.door !== 'command' || e.agentId) {
      return next(e)
    }
    const content = e.message.content.map(block =>
      block.type === 'text' ? { ...block, text: hideCommandArgs(block.text) } : block,
    )
    return next({ ...e, message: { ...e.message, content } })
  }).catch(($, e, next) => next(e))

  on('ui.close', async ($, e, next) => {
    if (e.id !== PANE || e.origin.kind !== 'person') {
      return next(e)
    }
    await update($, aside, a => ({ ...a, isConfirming: true }))
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Markdown, Input, Button } = $.ui.resolve(e)
    const state = await read($, aside)
    const last = state.entries.at(-1)

    return (
      <Box flexDirection="column">
        {state.entries.map(entry =>
          entry.kind === 'question' ? (
            <Text bold>{'> ' + entry.text}</Text>
          ) : entry.kind === 'tool' ? (
            <Text dimColor>{'● ' + entry.text}</Text>
          ) : (
            <Markdown text={entry.text} />
          ),
        )}
        {state.isBusy && last?.kind !== 'answer' && (
          <Text dimColor>{state.forkId ? 'thinking…' : 'starting fork…'}</Text>
        )}
        {state.error && <Text color="error">{state.error}</Text>}
        {state.isConfirming ? (
          <Box gap={1}>
            <Text>Discard this aside?</Text>
            <Button variant="primary" autoFocus onPress={() => void discard($)}>Discard</Button>
            <Button onPress={() => void update($, aside, a => ({ ...a, isConfirming: false }))}>Keep</Button>
          </Box>
        ) : (
          <Box flexDirection="column">
            <Input
              key="question"
              autoFocus
              placeholder={state.isBusy ? 'Wait for the answer…' : 'Ask a question…'}
              submitLabel="send"
              onSubmit={value => value.trim() && void ask($, value.trim())}
            />
            <Box gap={1}>
              {state.forkId && !state.isBusy && (
                <Button variant="primary" onPress={() => void promote($)}>Promote</Button>
              )}
              <Button role="dismiss" onPress={() => void update($, aside, a => ({ ...a, isConfirming: true }))}>Close</Button>
            </Box>
          </Box>
        )}
      </Box>
    )
  })
}
