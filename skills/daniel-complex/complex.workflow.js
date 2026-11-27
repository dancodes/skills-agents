export const meta = {
  name: 'daniel-complex',
  description: 'Fan out briefed workers (Sonnet by default), each writing full output to a file and returning a short summary, with an optional Opus merge',
  phases: [
    { title: 'Work', model: 'sonnet' },
    { title: 'Merge', model: 'opus' },
  ],
}

const calls = args.calls || 15
const outDir = args.outDir
const workers = args.workers || []

if (!outDir) throw new Error('args.outDir is required')
if (!workers.length) throw new Error('args.workers is empty')
if (workers.length > 10) throw new Error('more than 10 workers: ask Daniel first')

const outPath = w => `${outDir}/${w.label}.md`

const brief = w => `${args.cwd ? `Work in ${args.cwd}.\n` : ''}Overall task: ${args.task}

Goal: ${w.goal}
Scope: ${w.scope}
${w.edits ? 'You may edit files in your scope only.' : 'Read only. Change nothing.'}
Ruled out: ${w.ruledOut || 'nothing yet'}
Done when: ${w.doneWhen}

Budget: at most ${calls} tool calls. Count them. At the budget, stop and list what is left.
Write your full findings, with file:line, to ${outPath(w)}.
Reply with at most 10 lines: the result, the file path, and anything you are unsure of.`

phase('Work')
const results = await parallel(workers.map(w => () =>
  agent(brief(w), { label: `complex:${w.label}`, phase: 'Work', model: w.model || 'sonnet' })
    .then(summary => summary && { label: w.label, file: outPath(w), summary }),
))

const done = results.filter(Boolean)
const missing = workers.map(w => w.label).filter(l => !done.some(r => r.label === l))
if (missing.length) log(`No result from: ${missing.join(', ')}`)

if (!args.merge || !done.length) return { results: done, missing }

phase('Merge')
const merged = await agent(
  `Overall task: ${args.task}

Read these worker output files and merge them into one answer:
${done.map(r => `- ${r.file}`).join('\n')}

Resolve conflicts by checking the code. Mark a fact only one worker found as unconfirmed.
Write the full merge to ${outDir}/merge.md.
Reply with at most 15 lines: the merged answer, the conflicts and how you settled them.`,
  { label: 'complex:merge', phase: 'Merge', model: 'opus' },
)

return { results: done, missing, merged }
