---
name: daniel-complex
description: Split big work across subagents and workflows, with Sonnet for mechanical work and Opus for judgment, so the main context gets only summaries. Use when a task has 2 or more independent parts, or needs more than about 10 file reads or tool calls. Skip it for one question, one file or one small edit.
---

# /daniel-complex

You are the coordinator. Your context holds the plan, the briefs and the summaries. The reading, the digging and the mechanical edits happen in subagents.

## 1. Inline or delegate

Do a part **inline** when it takes 3 tool calls or fewer, or under about 300 lines of reading. Delegate every other part.

Light recon inline is fine: list files, one grep, read a signature. Do just enough to write precise briefs.

## 2. Split and pick a model

Split the work into parts that do not depend on each other. Give each part one model:

| Model | Jobs |
|---|---|
| `sonnet` (default) | find files, read and summarise, apply a written plan, mechanical edits, run tests and report |
| `opus` | design, root cause, review, merging results that conflict |

Set `model` explicitly on every Agent call and every workflow `agent()`. Sonnet and Opus only.

## 3. Pick the tool

- **Workflow**: 3 or more agents whose shape is known before they start, such as a fan-out or a pipeline (review, then verify).
- **Agent tool**: 1 or 2 agents, or when the next step depends on reading a result first.

Loading this skill is your opt-in to workflows of up to 10 agents.

## 4. Say the plan

Before you spawn, write one line, e.g. `3 Sonnet agents: routes, models, tests; then I merge`. Then spawn at once. For more than 10 agents, show the plan and wait for an OK.

## 5. Brief

Every brief carries all of these fields:

- **Goal**: one sentence.
- **Scope**: the files or folders it may touch, and whether it may edit.
- **Ruled out**: what you already know or excluded.
- **Done when**: one checkable condition.
- **Budget**: 15 tool calls for Sonnet. At the budget it stops and lists what is left.
- **Output**: full findings to `<scratchpad>/complex/<label>.md`, and a reply of 10 lines or fewer with the file path.

A brief is the agent's only context. Name exact paths, symbols and commands.

## 6. Collect

Read the summaries, not the output files. Open an output file only when a summary is unclear or two summaries disagree.

Merge the summaries yourself. Spawn one `opus` merge agent over the output files only when the results conflict or are too big to merge from summaries.

Before you act on a claim (an edit, a decision, a report to Daniel), spot-check it with one or two tool calls.

## 7. When a part fails

A Sonnet agent reports it is unsure, hits its budget, or fails your spot-check: rerun that part once with `opus` on a narrower scope. If Opus also fails, stop and ask Daniel.

## Rules

- Parallel agents edit separate files only. When two parts touch the same file, run them one after the other.
- Code that will be committed goes through `/daniel`. This skill covers research, analysis, checks and throwaway edits.

## Recipes

- A quick look from 5 angles: `/daniel-fastcheck`.
- Any other fan-out of briefed workers: run the Workflow tool with `scriptPath` set to `complex.workflow.js` in this skill's directory and `args`:

```json
{
  "task": "<one line on the overall task>",
  "cwd": "<directory>",
  "outDir": "<scratchpad>/complex",
  "calls": 15,
  "merge": false,
  "workers": [
    {"label": "routes", "goal": "...", "scope": "...", "ruledOut": "...", "doneWhen": "...", "edits": false, "model": "sonnet"}
  ]
}
```

`model` defaults to `sonnet`, `edits` to `false`. Set `merge: true` only when you already expect conflicting or large results. It adds one `opus` merge agent at the end.
