---
name: swarm
description: Deliver a change through many short Sonnet agents that coordinate on a shared message board in /tmp, each holding one card of at most five minutes. Use when the user invokes /swarm with a change request or a path to a markdown file.
---

# /swarm

Input: `/swarm <change request>` or `/swarm <path/to/request.md>`.

You are the orchestrator. You read the board, write cards, and spawn agents. You never read code, run tests, or edit files: every fact about the repo reaches you as a post.

## The board

One run, one folder: `/tmp/swarm/<run-id>/`, where `<run-id>` is `<yyyymmdd-hhmm>-<kebab-slug>`.

```
brief.md          the request, verbatim, plus the done criterion. Only you write it.
cards/C01.md      one card per unit of work. Only you write cards.
posts/P001-C01-scout.md   one file per post. Agents write posts, never edit one.
decisions.md      what the judge settled. Only you write it, from verdict posts.
```

One file per post means parallel agents never write the same file. Number posts with the next free `P###`; on a clash, take the next number.

### Card

```
---
id: C04
role: implementer
phase: implement
reads: [P007, P012, decisions.md]
budget: 15 tool calls
---
Goal: one sentence.
Done when: one checkable condition.
Files: at most two paths, or "none".
```

A card is small when its goal is one question or one change, its done condition is checkable, and it names at most two files. If you cannot write a card that way, split it.

### Post

```
---
from: C04-implementer
to: all | judge | C07
kind: finding | idea | verdict | change | test | attack | question | answer | split | blocked
---
At most 150 words. Cite file:line. State facts, not plans.
```

Agents talk through posts. A `question` names who should answer in `to:`. You route it: send it to the named agent with SendMessage if it is still running, or write an `answer` card for a fresh agent. A `split` post says the card is bigger than its budget and proposes the smaller cards; the agent stops there.

## Roles

Every agent is Sonnet. Spawn each one with the Agent tool, `subagent_type: "general-purpose"` and `model: "sonnet"`, on every call. A `fork` ignores `model` and runs on your own model, so never use one. Each agent gets the agent preamble below plus its card.

- **scout**: answers one question about the code. Posts `finding`.
- **ideator**: proposes one approach to the brief, given the findings. Posts `idea` with the files it would touch and its main risk.
- **judge**: compares the ideas against the findings and picks one, or asks for one more scout. Posts `verdict`. Judges only what is on the board.
- **implementer**: makes the one change on its card. Posts `change` with the diff hunk.
- **tester**: writes or updates one test for one behaviour and runs it. Posts `test` with the command and its result.
- **adversary**: tries to break one change: a caller it misses, an edge case, a rule in CLAUDE.md it breaks. Posts `attack`, or `finding: holds` with what it tried.
- **verifier**: runs `yarn typecheck`, `yarn lint`, and the touched test files. Posts the exit codes and the first failure verbatim.

### Agent preamble

```
You hold card <id> on the board at <board path>. Read brief.md, your card,
and every file in your card's `reads`. Skim the post filenames for anything
addressed to you. Do the card and nothing else. Stay within the budget on
the card. When done, write one post and stop. If the card is bigger than
its budget, write a `split` post instead. If you need a fact another agent
owns, write a `question` post and stop.
```

## Flow

Each phase ends when every card in it has a post. Spawn a phase's cards in one message so they run in parallel.

1. **Brief.** Create the board. Write `brief.md` with the request and one done criterion the verifier can check. Show the user `brief.md` and wait. Spawn no agent until the user explicitly says go.
2. **Scout.** Write 3 to 6 scout cards, one question each (where does X live, who calls Y, which tests cover Z, what do the CLAUDE.md files under that path demand). Answer any `question` posts with more scout cards.
3. **Ideate.** Write 2 or 3 ideator cards, each reading every finding. Ask each for a different angle: smallest diff, root cause, reuse of existing code.
4. **Judge.** One judge card reading every idea and finding. Copy the verdict into `decisions.md`. If the judge asks for another scout, run it and judge again. Stop after two rounds and ask the user.
5. **Plan.** Turn the chosen idea into implementer and tester cards, one change or one test each. Show the user the card list and wait for approval.
6. **Implement.** Implementers and testers edit the current working copy. Use a jj workspace only when the user's request asks for one: then create it with `~/.claude/skills/daniel/new-workspace.sh <slug>` and pass its path on every implementer and tester card. Cards whose files overlap run one after another; cards with disjoint files run in parallel.
7. **Attack.** One adversary card per `change` post. An `attack` that holds becomes a new implementer or tester card, and goes back through this step.
8. **Verify.** One verifier card. A failure becomes one implementer card for that failure, then verify again. Stop after three rounds and report the failure.
9. **Report.** Relay to the user: the verdict, every `change` post's hunk verbatim, the verifier's result, and any attack left open, and the workspace path if one was used. Leave the board and any workspace in place for review. The run ends here: commits, bookmarks and landing are the user's call.
