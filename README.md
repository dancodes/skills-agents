# skills-agents

Claude Code skills, agents, hooks and mods for implementing changes in a jj repository
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
Each repo skill directory replaces its installed copy whole, so files deleted
from the repo are deleted there too. Skills not in this repo are left alone.
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

## Mods

`mods/` is a local plugin marketplace named `daniel-mods`. Each mod is a
plugin directory in it, listed in `mods/.claude-plugin/marketplace.json`.
`install.sh` registers the marketplace and installs every listed mod, so they
load in place from the repo: edit a mod, then run `/reload-plugins`. Run a
mod's tests with `claude plugin test mods/<name>`.

| Mod | What |
|---|---|
| `usage-footer` | 5h and weekly usage, with time to reset, in the prompt footer |
| `guards` | global hooks: `forbidden-commands.py --global` (also bans Monitor and `sleep`), `push-guard.py`, `conflict-tripwire.py`, `question-turn.py` |
| `tool-timer` | shows `took 12.4s` under a tool call's row when it ran past `thresholdSeconds` (default 5) |

To add a mod, create `mods/<name>/` and add `{ "name": "<name>", "source": "./<name>" }`
to the marketplace's `plugins`, then run `./install.sh`.

## Flow

| Stage | Who | What |
|---|---|---|
| implement | `impl` in its workspace | edits + `jj status` to snapshot; never commits |
| comment pass | `/no-comments` inside `impl` | `impl` deletes its own comments and applies local `MUST KILL` reshapes inline |
| commit a round | `/daniel` via `commit-workspace.sh` | on `continue`: `jj describe` + `jj new`, so the next round is a follow-up commit; workspace and `impl` agent stay alive |
| park | `/daniel` via `park-workspace.sh` | `jj describe` + `jj bookmark create handoff/<name>` on the tip of the workspace's stack, then forgets the workspace and deletes its directory |
| integrate | `/daniel-integrate` → `jj` agent | runs one preflight report, acquires lock, squashes each commit a `handoff/*` carries into the feature line oldest first, verifies each batch, deletes bookmark, releases lock |
| clean up | anyone via `cleanup-workspace.sh [name...]` | forgets and deletes leftover workspaces under `daniel-workspaces` that hold no unparked work; skips stale ones |

`new-workspace.sh` runs the repo profile's `setup-workspace.sh`, which can
link dependencies, generated files and warm caches into the new workspace.

Implementation and integration are separate invocations. `/daniel` leaves the
work parked and stops. `/daniel-integrate` is the only writer to the feature
line, and it holds a lock for its whole run, so two runs finishing at once
cannot rewrite the same commits concurrently. That is what leaves changes
divergent, other workspaces stale, and un-snapshotted edits gone.

## Private repo profiles

Nothing here is specific to one company or repo. Repo-specific and private
data lives outside this repo, in `${SKILLS_AGENTS_PRIVATE:-$HOME/.config/skills-agents}`:

```
ticket.md                     Linear team id and key, assignee, cycle rule, branch glob
push-allow                    bookmark globs, one per line, push-guard.py pushes without asking
repos/<name>/match            a path relative to the workspace root; the profile applies when it exists
repos/<name>/scaffolding      extra scaffolding directories, one per line (node_modules is built in)
repos/<name>/setup-workspace.sh <source-root> <workspace-root>   run by new-workspace.sh
repos/<name>/notes.md         test commands, test conventions and commit order, read by impl and jj
repos/<name>/forbidden.json   extra [regex, message] rules for hooks/forbidden-commands.py
repos/<name>/verify.sh        daniel-verify profile: PORTS, ENV_FILE, HEALTH_PATH, TEMPLATES,
                              app_dir, prestart, dev_env, dev_command
repos/<name>/verify.md        login, templates, target preparation and routes for agents
```

`skills/daniel/repo-profile.sh` finds the profile for a path. Every file is
optional; without a profile the skills fall back to the repo's CLAUDE.md and
plain defaults.

## Browser verify setup

`/daniel-verify` needs, once per machine:

- TigerVNC and jq: `sudo apt install tigervnc-standalone-server jq`.
- Chrome for Testing, linked at `~/.cache/daniel-verify/chrome-bin`. Take the
  linux64 `chrome` URL for Stable from
  `https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json`,
  unzip it under `~/.cache/daniel-verify/browsers/`, and link the binary.
- On Ubuntu 23.10 or later, an AppArmor profile so Chrome keeps its sandbox:
  ```
  sudo tee /etc/apparmor.d/daniel-verify-chrome <<'APPARMOR'
  abi <abi/4.0>,
  include <tunables/global>
  profile daniel-verify-chrome /home/*/.cache/daniel-verify/browsers/**/chrome flags=(unconfined) {
    userns,
  }
  APPARMOR
  sudo apparmor_parser -r /etc/apparmor.d/daniel-verify-chrome
  ```
- A `chrome-devtools` MCP server with `--browser-url=http://localhost:9222`.
