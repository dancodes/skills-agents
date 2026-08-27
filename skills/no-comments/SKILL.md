---
name: no-comments
description: Spawn the comment-sicko agent over the work just implemented, vet its report, and apply the accepted deletions and reshapes. Invoked by the impl agent after implementing and before reporting back, never by a human.
---

# /no-comments

The final pass over the comments in the work you just did. You wrote those
comments, so you will defend them. That is why a fresh agent judges them
instead. Defer to it.

## Scope

The files you changed in this workspace, and only the comments inside the
changed hunks. Get the list with `jj diff --summary` in the workspace
directory.

## Steps

1. Spawn the `comment-sicko` agent with the workspace directory and the file
   list. Do not restate its rules, it has them. It deletes comments and reports.
   It runs in the background, so its report reaches you as a notification some
   time after the spawn call returns. Wait for that notification. Until it
   arrives you have nothing to vet: do not move to step 2, do not write your
   report, do not end your turn, and never guess what it found. Spawn exactly
   one and wait, rather than spawning a second because the first is slow.
2. Read its report and `jj diff --git` for every file it touched. Reject:
   - any edit to application code, or to a file or hunk outside the scope,
   - a deletion whose comment matches an exception it was given, where the proof
     is in front of you today.
   Restore only those. A comment you merely liked is not a rejection. If a
   deletion is ambiguous, it stays deleted.
3. Apply the `MUST KILL` flags that are a local fix inside the scope: a rename,
   an extract, a type, a dead path dropped, the real API used instead of a
   worked-around one. Fix the root cause, not the symptom.
4. A flag needing a change wider than the scope is not yours to make here.
   Leave the code alone and carry it into your report as open work.
5. Run `jj status` in the workspace. The deletions came from another agent's
   edits and are only on disk until something snapshots them.

## Report

One line back to the orchestrator, above your diff hunks: the deletion count,
anything you restored and why, the `MUST KILL` flags you fixed, and the ones
left open.
