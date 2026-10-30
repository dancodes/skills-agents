export const meta = {
  name: 'daniel-fastcheck',
  description: 'Fast pass over one subject with 5 Sonnet agents, one angle each, on a small tool call budget',
  phases: [{ title: 'Check', model: 'sonnet' }],
}

const DEFAULT_ANGLES = [
  'Where it lives: the files, functions and config that define it.',
  'How it is used: callers, entry points and data flow.',
  'What could be wrong: bugs, gaps, stale or contradicting code.',
  'Tests and checks: what covers it and what does not.',
  'Surprises: anything odd a newcomer would trip on.',
]

const angles = (args.angles && args.angles.length ? args.angles : DEFAULT_ANGLES).slice(0, 5)
const calls = args.calls || 8

phase('Check')
const reports = await parallel(angles.map((angle, i) => () =>
  agent(
    `Fast pass. Read only. Change nothing.${args.cwd ? `\nWork in ${args.cwd}.` : ''}

Subject:
${args.task}

Your angle: ${angle}

Hard budget: at most ${calls} tool calls in total. Count them. Stop at the budget, even if unsure.
Batch independent calls in one turn. Prefer one grep over many reads.
Return at most 10 short bullets of facts with file:line, then one line of what you did not get to.`,
    { label: `fastcheck:${i + 1}`, phase: 'Check', model: 'sonnet', effort: 'low' },
  )
))

return reports.map((report, i) => report && { angle: angles[i], report }).filter(Boolean)
