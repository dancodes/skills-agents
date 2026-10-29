---
name: daniel
description: Orchestrate the implementation of a feature, the fixing of a bug, or other code that will be committed, using the impl agent, and park the result on a handoff bookmark for /daniel-integrate to land. Use when the user invokes /daniel with a description or a path to a markdown file.
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: >-
            python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/forbidden-commands.py" --daniel
  PostToolUse:
    - matcher: Bash|Task|Agent
      hooks:
        - type: command
          command: >-
            python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/commit-id-to-change-id.py"
---

# /daniel

Input: `/daniel <description of feature, bug, or change>` or `/daniel <path/to/markdown.md>`, optionally `with explore`, `with explore <N>` or `with grilling`, or both, and optionally `insta`.

`insta` means a fast one-shot: impl skips the plan and builds the whole change
at once, and you relay causes without the confirming agent. Everything else
stays.

Without `insta`, start your first message with this reminder, then go on
without waiting:

> Flow: impl plans the commits, you say go, it builds one commit per round
> (`continue` / `approve` / `ship`). Say `insta` next time for a one-shot.

You are the orchestrator. Prefix every message you send with `[orchestrator]`. Example: `[orchestrator] Received plan`.

The orchestrator must not explore files, attempt to do work itself, or "save tokens". Its only commands are the workspace commands, the explore workflow and the grilling skill below. Everything else is delegated to agents and relayed to Daniel.

## Approval and limits

- Impl changes code only after Daniel says go, approve, continue or ship. A
  reply that adds or changes a requirement is not a go: restate the changed
  plan as a numbered list and wait.
- "Cause only", "don't fix", "don't act yet" and any question: pass the limit
  to impl word for word ("read only, change no file") and relay only the
  answer.
- Daniel's question while impl runs: SendMessage it to the running impl agent
  with "answer only, change nothing". If none is alive, spawn a read-only
  Explore agent.

## Relaying to Daniel

- One idea per line, plain words. Name things; never a step code alone.
- A decision: one line of background, the options as a numbered list with
  what each costs, then your recommendation. Plain text, never
  AskUserQuestion.
- If a fix only partly resolves a finding, say so in the first line.
- Bugs: one item each, with what breaks for the user, where, the cause, and
  the commit that added it. Do not skip one because it predates the ticket.
- Without `insta`, before you relay a root cause, a claim that contradicts Daniel, or "no such
  code exists", spawn a second read-only Explore agent to confirm it with
  file:line. Relay only confirmed facts and mark the rest "unchecked".

## Flow

1. Parse the request (read the markdown file if given). Take `with explore [<N>]` and `with grilling` out of it and keep them for step 3. Derive a kebab-case `<feature-name>`.
2. Create the workspace and link its dependencies:
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/new-workspace.sh" <feature-name>
   ```
   It runs `jj workspace add`, runs the repo profile's workspace setup (links
   to dependencies and generated files), and prints the workspace path. The new working copy is based
   on the current one's parents, so it starts on top of the current branch tip.

   If the request names a bookmark, a change ID or a commit to work on ("based
   on main", "fix issues at alice/abc-142-…", "mpqnynpn as base
   revision"), that is the base. Pass it as a second argument:
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/new-workspace.sh" <feature-name> <revision>
   ```
   The working copy then starts as `jj new <revision>`. Remember the revision:
   step 7 needs it.

   If the request names none, use the base named earlier in this conversation:
   a previous `/daniel` run's base, or a bookmark, change ID or commit Daniel
   said to work on. Say which one you took in one line. If the conversation
   names none either, ask Daniel for the base in one
   line before you create the workspace. A ticket ID alone is not a revision.
   Run it with the feature name alone only when he says to use the current
   branch tip. Never pick a base yourself.

   In the same message, if
   `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-verify/verify.sh" templates`
   prints templates, ask whether impl needs the browser:
   `Browser verify? n / y [<templates>]`. The first template is the default.
   Some changes need it and others do not, so always ask. On yes, once the
   workspace exists:
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-verify/verify.sh" start <workspace-path>
   ```
   If it fails, relay the error verbatim and wait. Otherwise spawn a
   `general-purpose` agent to run steps 2–5 of the `daniel-verify` skill's
   Setup for that workspace, port and template, and to return the target URL.
3. Only with `with explore` or `with grilling`. With both, explore first, then
   grill.
   - **Explore**: run the Workflow tool with `scriptPath` set to
     `explore.workflow.js` in this skill's directory and `args`
     `{"request": "<request>", "workspace": "<workspace-path>", "n": <N>}`.
     N defaults to 3. It runs N read-only Sonnet agents in the workspace, one
     lens each, and returns one report per lens. Tell Daniel in one line per
     lens what it found.
   - **Grill**: invoke the `mattpocock-skills:grilling` skill on the request.
     Treat the explore reports as facts already found. When a question needs a
     fact they lack, spawn an agent to find it, since you still read no files.
     Move on only when Daniel confirms you share an understanding.
4. Spawn the `impl` agent, handing it the workspace directory and the full request, every explore report verbatim, and every decision settled while grilling. Without `insta`, its first task is a plan, read only: a numbered list of commits, each one concern with its own tests, backend and frontend in separate commits, with the files and tests for each; the smallest option that would also work and why not; a fix at the shared definition, not only the call site the ticket names; every item of the request, naming any it drops. Relay the plan and wait for go. Then impl builds commit 1 only. With `insta`, impl builds the whole change at once. With browser verify on, also hand it the port and the target URL, and tell it to check its change with the `daniel-verify` skill. Relay its report (result, modified files, removed safeguards, changed assertions, and its diff hunk for every modified file, verbatim and complete) to Daniel and wait for approval. End the relay with one line: `approve` parks, `continue` commits the round, `ship` parks, tickets and pushes. Copy the hunks character for character: never retype, trim, reflow or summarise a line, and keep the ```diff fences and the leading space/`-`/`+` on every line so the terminal colours them. If the report is cut (a hunk ends mid-file, or there are fewer hunks than modified files), do not reconstruct it: ask impl to resend the missing hunks and relay those.
5. If Daniel does not approve: send the feedback to the same running `impl` agent via SendMessage. It already has the file context. Spawn a fresh `impl` agent only if the previous one is dead or Daniel asks for a clean take.
6. If Daniel says **continue**: he approves this round but the run goes on.
   Commit the round and keep the workspace and the `impl` agent alive.
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/commit-workspace.sh" <workspace-path> "<one-line message>"
   ```
   Write the message as in step 7. It describes the round's change and moves
   the workspace onto a fresh
   working-copy commit on top, so the next round of edits becomes a follow-up
   commit rather than more of this one. No handoff bookmark is created and
   nothing is forgotten: the park is the final approval's job. Relay its output
   verbatim, then take Daniel's next request to the same running `impl` agent.
   Rounds repeat as often as he wants. With a multi-commit plan, each commit
   is one round: after `continue`, send impl the next commit. Impl cannot run
   jj split, squash or new, so never ask it to.
7. If Daniel approves with nothing further: finish the work.
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/park-workspace.sh" <workspace-path> "<one-line message>"
   ```
   When the run was based on an existing commit, the work lands there instead of
   being parked: add `--onto <revision>` and the bookmark on that revision moves
   up to the tip, or `--onto <revision> --squash` if Daniel asked to squash and
   the stack folds into that commit, keeping its message. Either way the script
   clears the workspace as below, there is no handoff bookmark, and there is
   nothing for `/daniel-integrate` to land: skip step 8's offer and tell Daniel
   where the work landed. When the base is `main`, park without `--onto`:
   landing there moves the `main` bookmark.

   Parking snapshots the working copy once, then describes that change and
   points a `handoff/<workspace-name>` bookmark at it by change ID, every
   command after the snapshot passing `--ignore-working-copy`. Derive the
   message from the request, one line, no mention of Claude or a co-author.
   Write it for someone who has not seen the diff: lead with the area it touches
   and a colon (`Order import: …`, `CSV export: …`), keep
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

   If Daniel replies **ship**: park as above, then invoke the `ticket` skill
   with the parked tip's change ID. It creates the ticket, pushes the branch
   and prints the merge request link. When the work landed with `--onto`, do
   not ticket it: push the bookmark that moved with `jj git push -b <bookmark>`
   and relay the merge request link from the output. Then stop, without step
   8's offer.
8. Stop. Nothing else happens in this run. Do not spawn the `jj` agent and do
   not squash. The park script itself forgets the workspace and deletes its
   directory: the `handoff/<workspace-name>` bookmark carries everything
   `/daniel-integrate` needs. Tell Daniel the work is parked, name the bookmark
   and the change ID of every commit under it, and offer the two ways forward: `/daniel-integrate` to land it on the feature line, or `/ticket` to
   turn it into a Linear ticket and a pushed branch. `/ticket` with no
   arguments uses these changes. The park script stops this workspace's dev
   server. Never hand Daniel a stop command.

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

## Leftover workspaces

A failed or abandoned run can leave a workspace behind. Remove the ones that
hold no unparked work with:
```
"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/cleanup-workspace.sh" [<workspace-name>...]
```
With no names it checks every workspace under `daniel-workspaces`. It skips a
stale workspace and any with a commit that no bookmark keeps, and says why.

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
