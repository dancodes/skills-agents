---
name: daniel-integrate
description: Land the work that /daniel runs have parked on handoff bookmarks into the feature line, one handoff at a time, under a lock. Use when the user invokes /daniel-integrate, or asks to integrate, land, or squash parked work.
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

# /daniel-integrate

Input: `/daniel-integrate` for everything parked, or `/daniel-integrate <handoff-name ...>` to
land only the named ones.

You are the integration owner. Prefix every message you send with `[integrate]`.

This is the only place the feature line is rewritten. Concurrent squashes into
the same commits are what left changes divergent, workspaces stale, and
un-snapshotted edits gone, so this skill is single-writer and holds a lock for
its whole run.

You do not explore files, review code, or decide targets. You hold the lock,
list what is parked, drive the `jj` agent, and relay. The workspace you run in
is the integration workspace: never `cd` into a parked workspace.

## Flow

1. Acquire the lock. Nothing else happens until this succeeds.
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-integrate/integrate-lock.sh" acquire
   ```
   If it fails, another integration run holds it. Relay its output to Daniel and
   stop. Do not remove the lock directory yourself, and do not proceed without
   it.
2. List what is parked:
   ```
   jj log -r 'bookmarks(glob:"handoff/*")' --no-graph \
     -T 'bookmarks.join(" ") ++ "  " ++ change_id.shortest(8) ++ "  " ++ description.first_line() ++ "\n"'
   jj workspace list
   ```
   Nothing parked means nothing to do: release the lock and say so.
3. Relay the list to Daniel with the file count per handoff, and confirm which
   handoffs to land and in what order. Refactors first, then backend, then
   frontend, per the order the `jj` agent enforces. If Daniel named handoffs in
   the invocation, confirm that list rather than asking again.
4. Spawn one `jj` agent for the whole run, handing it this workspace's directory
   and the confirmed handoff bookmarks in order. It plans only. Relay its plan
   (per-file target, commit vs squash, messages, blast radius) and wait for
   approval.
5. If Daniel rejects the plan: send the feedback to the same running `jj` agent
   via SendMessage. It replans without touching the repository.
6. If Daniel approves: tell the same `jj` agent to execute. It works in batches
   of at most five squashes and reports between batches. Relay each report and
   wait before telling it to continue.
7. If Daniel rejects an executed result: send the feedback to the same running
   `jj` agent. It corrects forward.
8. If Daniel approves the result: tell the `jj` agent to clean up each landed
   handoff. Relay its confirmation.
9. Release the lock, always, whether the run finished, was rejected, or was
   abandoned:
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-integrate/integrate-lock.sh" release
   ```
   If Daniel stops the run midway, release it before you finish your last
   message. A lock left behind blocks every later integration.

## One handoff at a time

The `jj` agent may plan all the confirmed handoffs together, because the
per-file targets of one can change the correct target of the next. It executes
them one at a time, and a handoff is fully landed and verified before the next
one starts. Never let two handoffs be mid-squash together.

## Cleanup, per landed handoff

The `jj` agent runs the first two from this workspace; the last is Daniel's,
because auto mode blocks it:

```
jj bookmark delete handoff/<name>
jj workspace forget <name>
rm -rf ../daniel-workspaces/<name>
```

The bookmark has to go: after the squash its commit is empty, and leaving the
bookmark keeps that empty commit visible and makes the handoff look unlanded.
Give Daniel the `rm -rf` with a `!` prefix so he can run it in his chat window.

## A parked workspace that has gone stale

Irrelevant to you. The handoff bookmark is the source of truth, and it holds the
snapshot the park took. A stale or already-forgotten workspace does not block
integration: the `jj` agent reads and squashes `handoff/<name>` by revision from
this workspace.

Never run `jj workspace update-stale` in a parked workspace, and never let the
`jj` agent do it. A hook blocks it under `daniel-workspaces`.

If a handoff is divergent, both sides are visible in `jj log -r 'divergent()'`
and named by change offset, `<change-id>/0` for the most recent and `/1` for the
one before. Report which side holds the files and let the `jj` agent squash from
that one.
