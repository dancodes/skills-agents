export const meta = {
  name: 'daniel-explore',
  description: 'Explore the codebase for a /daniel request with N read-only Sonnet agents, one lens each',
  phases: [{ title: 'Explore', model: 'sonnet' }],
}

const LENSES = [
  'Where the change lands: the files, functions and types that must be edited.',
  'Patterns to copy: the closest existing feature or fix in this codebase, and how it is wired end to end.',
  'Callers and dependents: everything that calls or imports the code that will change, and what would break.',
  'Tests: the tests that cover this area, how to run them, and which ones the change should extend.',
  'Data and contracts: the schemas, API shapes, migrations and config the change touches.',
  'Conventions and traps: repo docs, learnings files, lint rules and naming the change must follow, and anything likely to surprise whoever implements it.',
]

const asked = args.n || 3
const lenses = LENSES.slice(0, Math.max(1, Math.min(asked, LENSES.length)))
if (asked > LENSES.length) log(`Asked for ${asked} explorers, ran ${LENSES.length}`)

phase('Explore')
const reports = await parallel(lenses.map((lens, i) => () =>
  agent(
    `Explore the codebase in ${args.workspace} for the request below. Read only. Change nothing.

Request:
${args.request}

Your lens: ${lens}

Report facts with file:line, not advice. Say what you looked for and could not find.`,
    { label: `explore:${i + 1}`, phase: 'Explore', model: 'sonnet', agentType: 'Explore' },
  )
))

return reports.map((report, i) => report && { lens: lenses[i], report }).filter(Boolean)
