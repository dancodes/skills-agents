import type { Aside, AsideEntry } from '../types'

type Block = { type: string; name?: string; input?: Record<string, unknown> }

const toolLine = (block: Block) => {
  const target = Object.values(block.input ?? {}).find(value => typeof value === 'string') ?? ''
  return `${block.name}(${String(target).slice(0, 80)})`
}

const appendAnswer = (entries: AsideEntry[], text: string): AsideEntry[] => {
  const last = entries.at(-1)
  return last?.kind === 'answer'
    ? [...entries.slice(0, -1), { kind: 'answer', text: last.text + text }]
    : [...entries, { kind: 'answer', text }]
}

export const applyLine = (aside: Aside, line: string): Aside => {
  let event
  try {
    event = JSON.parse(line)
  } catch {
    return aside
  }

  if (event.type === 'system' && event.subtype === 'init') {
    return { ...aside, forkId: event.session_id }
  }
  if (event.type === 'stream_event' && event.event?.delta?.type === 'text_delta') {
    return { ...aside, entries: appendAnswer(aside.entries, event.event.delta.text) }
  }
  if (event.type === 'assistant') {
    const tools = (event.message?.content ?? []).filter((block: Block) => block.type === 'tool_use')
    if (tools.length === 0) {
      return aside
    }
    const lines: AsideEntry[] = tools.map((block: Block) => ({ kind: 'tool', text: toolLine(block) }))
    return { ...aside, entries: [...aside.entries, ...lines] }
  }
  if (event.type === 'result') {
    return { ...aside, isBusy: false, error: event.is_error ? String(event.result ?? 'The fork failed.') : null }
  }
  return aside
}

export const hideCommandArgs = (text: string) =>
  text.includes('<command-name>/aside</command-name>')
    ? text.replace(/<command-args>[\s\S]*?<\/command-args>/, '<command-args></command-args>')
    : text
