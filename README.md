# skills-agents

Claude Code skills, agents and hooks for implementing changes in a jj repository
that several agents work in at once.

## Install

Prerequisites:

- Claude Code, for the Claude install (always).
- The [pi coding agent](https://www.npmjs.com/package/@earendil-works/pi-coding-agent)
  with `pi install npm:pi-subagents`, for the Pi install (optional). Without
  the `pi` command on `PATH` the Pi install is skipped with a message.

```
./install.sh
```

Copies `skills/`, `agents/` and `hooks/` into `~/.claude` (or `$CLAUDE_HOME`).
When `pi` is installed, it also renders `skills/` and `agents/` for Pi via
`scripts/render-pi-markdown.py` and installs them into `~/.pi/agent` (or
`$PI_CODING_AGENT_DIR`):

- Hooks are stripped; Pi never runs Claude hooks.
- Claude tool names are mapped to Pi tool names (`Bash`→`bash`, `Read`→`read`,
  `Grep`→`grep`, `Glob`→`find`, `Edit`→`edit`, `Write`→`write`,
  `Agent`→`subagent`+`subagent_wait`); an unknown tool fails the install.
- Agents get `systemPromptMode: replace` and `inheritProjectContext: true`.
- Path expressions like `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` in skill and
  agent bodies are rewritten to `${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}`.

The rendered agents and skills are the only capability source: Pi uses the
same tool allowlists declared in the canonical agents, mapped to Pi's names.
`hooks/` are Claude-only and are never installed for Pi.

## Flow

| Stage | Who | What |
|---|---|---|
| implement | `impl` in its workspace | edits + `jj status` to snapshot; never commits |
| comment pass | `/no-comments` → `comment-sicko` | fresh agent deletes the comments `impl` wrote; `impl` vets and applies `MUST KILL` reshapes |
| park | `/daniel` via `park-workspace.sh` | `jj describe` + `jj bookmark create handoff/<name>`, then forgets the workspace and deletes its directory |
| integrate | `/daniel-integrate` → `jj` agent | acquires lock, squashes `handoff/*` into the feature line, deletes bookmark, releases lock |

Agents typecheck through `skills/daniel/typecheck.py`, which runs
`yarn typecheck --checkers 1`; a hook blocks `yarn typecheck`, `tsgo` and `tsc`
run directly. `new-workspace.sh` seeds each workspace with the incremental
cache, so a workspace's first typecheck is warm rather than cold, and with the
CodeGraph index, so `impl` can query the codebase instead of grepping it.

Implementation and integration are separate invocations. `/daniel` leaves the
work parked and stops. `/daniel-integrate` is the only writer to the feature
line, and it holds a lock for its whole run, so two runs finishing at once
cannot rewrite the same commits concurrently. That is what leaves changes
divergent, other workspaces stale, and un-snapshotted edits gone.
