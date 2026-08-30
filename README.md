# skills-agents

Claude Code skills, agents and hooks for implementing changes in a jj repository
that several agents work in at once.

## Install

```
./install.sh
```

Copies `skills/`, `agents/` and `hooks/` into `~/.claude` (or `$CLAUDE_HOME`).

## Flow

| Stage | Who | What |
|---|---|---|
| implement | `impl` in its workspace | edits + `jj status` to snapshot; never commits |
| comment pass | `/no-comments` → `comment-sicko` | fresh agent deletes the comments `impl` wrote; `impl` vets and applies `MUST KILL` reshapes |
| park | `/daniel` via `park-workspace.sh` | `jj describe` + `jj bookmark create handoff/<name>`, then stops |
| integrate | `/daniel-integrate` → `jj` agent | acquires lock, squashes `handoff/*` into the feature line, deletes bookmark, forgets workspace, releases lock |

Agents typecheck through `skills/daniel/typecheck.py`, which runs
`yarn typecheck --checkers 1`; a hook blocks `yarn typecheck`, `tsgo` and `tsc`
run directly. `new-workspace.sh` seeds each workspace with the incremental
cache, so a workspace's first typecheck is warm rather than cold.

Implementation and integration are separate invocations. `/daniel` leaves the
work parked and stops. `/daniel-integrate` is the only writer to the feature
line, and it holds a lock for its whole run, so two runs finishing at once
cannot rewrite the same commits concurrently. That is what leaves changes
divergent, other workspaces stale, and un-snapshotted edits gone.
