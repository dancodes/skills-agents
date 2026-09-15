---
name: daniel
description: Orchestrate the implementation of a feature, the fixing of a bug, or other code that will be committed, using the impl agent, and park the result on a handoff bookmark for /daniel-integrate to land. Use when the user invokes /daniel with a description or a path to a markdown file.
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: >-
            python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/forbidden-commands.py"
  PostToolUse:
    - matcher: Bash|Task|Agent
      hooks:
        - type: command
          command: >-
            python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/commit-id-to-change-id.py"
---

# /daniel

Input: `/daniel <description of feature, bug, or change>` or `/daniel <path/to/markdown.md>`.

You are the orchestrator. Prefix every message you send with `[orchestrator]`. Example: `[orchestrator] Received plan`.

The orchestrator must not explore files, attempt to do work itself, or "save tokens". Its only commands are the workspace commands below. Everything else is delegated to agents and relayed to Daniel.

## Flow

1. Parse the request (read the markdown file if given). Derive a kebab-case `<feature-name>`.
2. Create the workspace and link its dependencies:
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/new-workspace.sh" <feature-name>
   ```
   It runs `jj workspace add`, links the existing `node_modules` and generated
   API client in, and prints the workspace path. The new working copy is based
   on the current one's parents, so it starts on top of the current branch tip.

   If Daniel says the work goes on top of an existing commit, pass that
   revision as a second argument:
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/new-workspace.sh" <feature-name> <revision>
   ```
   The working copy then starts as `jj new <revision>`. Remember the revision:
   step 6 needs it.

   Otherwise run it with the feature name alone. A branch, bookmark, or ticket
   name in the request is context for the agents, not a base revision. If you
   think a different base is necessary, ask Daniel first, never decide it
   yourself.
3. Spawn the `impl` agent, handing it the workspace directory and the full request. Relay its report (result, modified files, and its diff hunk for every modified file, verbatim and complete) to Daniel and wait for approval. Never trim or summarise the hunks, and keep the ```diff fences and the leading space/`-`/`+` on every line so the terminal colours them.
4. If Daniel does not approve: send the feedback to the same running `impl` agent via SendMessage. It already has the file context. Spawn a fresh `impl` agent only if the previous one is dead or Daniel asks for a clean take.
5. If Daniel says **continue**: he approves this round but the run goes on.
   Commit the round and keep the workspace and the `impl` agent alive.
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/commit-workspace.sh" <workspace-path> "<one-line message>"
   ```
   Write the message as in step 6. It describes the round's change and moves
   the workspace onto a fresh
   working-copy commit on top, so the next round of edits becomes a follow-up
   commit rather than more of this one. No handoff bookmark is created and
   nothing is forgotten: the park is the final approval's job. Relay its output
   verbatim, then take Daniel's next request to the same running `impl` agent.
   Rounds repeat as often as he wants.
6. If Daniel approves with nothing further: finish the work.
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/park-workspace.sh" <workspace-path> "<one-line message>"
   ```
   When the run was based on an existing commit, the work lands there instead of
   being parked: add `--onto <revision>` and the bookmark on that revision moves
   up to the tip, or `--onto <revision> --squash` if Daniel asked to squash and
   the stack folds into that commit, keeping its message. Either way the script
   clears the workspace as below, there is no handoff bookmark, and there is
   nothing for `/daniel-integrate` to land: skip step 7's offer and tell Daniel
   where the work landed.

   Parking snapshots the working copy once, then describes that change and
   points a `handoff/<workspace-name>` bookmark at it by change ID, every
   command after the snapshot passing `--ignore-working-copy`. Derive the
   message from the request, one line, no mention of Claude or a co-author.
   Write it for someone who has not seen the diff: lead with the area it touches
   and a colon (`Backend sensitivity analysis: …`, `Wrap Up export: …`), keep
   code identifiers in backticks, and cut every word that identifies nothing —
   adjectives like "analysed", "given" or "existing" narrow no set. `/ticket`
   copies this line into the Linear title, where it is read in a list of
   hundreds with no context at all.
   The bookmark goes on the tip, so every round already committed with
   `commit-workspace.sh` is parked with it; the message given here describes the
   last round only, and the earlier commits keep the messages they were
   committed with. Relay the script's output verbatim: the bookmark, every
   commit it carries with its change ID and file list, and any scaffolding line
   it printed.
7. Stop. Nothing else happens in this run. Do not spawn the `jj` agent and do
   not squash. The park script itself forgets the workspace and deletes its
   directory: the `handoff/<workspace-name>` bookmark carries everything
   `/daniel-integrate` needs. Tell Daniel the work is parked, name the bookmark
   and the change ID of every commit under it, and offer the two ways forward: `/daniel-integrate` to land it on the feature line, or `/ticket` to
   turn it into a Linear ticket and a pushed branch. `/ticket` with no
   arguments uses these changes.

## Why parking, and not committing here

Integration is single-writer. `/daniel-integrate` is the only thing that
rewrites the feature line, it runs in the original workspace, and it holds a
lock while it does, so two runs finishing at once cannot rewrite the same
commits concurrently. That is what leaves changes divergent, other workspaces
stale, and un-snapshotted edits gone.

This run's only job is to leave the work on a bookmark that survives the
workspace going stale or being forgotten.

`continue` commits inside the impl workspace, which is not the feature line and
is nobody else's to read. It rewrites nothing shared, so it needs no lock.

## When the impl agent reports the working copy is stale

Expected: the repository moved under that workspace. It is not a failure and
nothing is lost as long as the edits were snapshotted.

Do not tell the agent to run `jj workspace update-stale`, and do not run it
yourself. It rewrites the files on disk to match a commit, discarding every edit
that was never snapshotted. A hook blocks it in a workspace under
`daniel-workspaces`.

Confirm the agent has copied its edited files to its scratchpad, then read the
snapshotted content from this workspace, never from inside the stale one. Name
the commit by its change ID, never by a working-copy reference like
`<workspace-name>@`, which resolves against a working copy you are not in:

```
jj --ignore-working-copy log -r 'divergent()'
jj --ignore-working-copy workspace list
jj --ignore-working-copy diff --summary -r <change-id>
```

`workspace list` prints each workspace's change ID next to its name.

If the change is divergent, both sides are visible and named by change offset:
`<change-id>/0` is the most recent, `/1` the one before. The side holding the
files is the one to park from. Relay what you found to Daniel and let him decide
before anything else runs.
