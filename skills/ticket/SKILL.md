---
name: ticket
description: Create one Linear ticket per jj change (branch tip), with a plain-English summary on top and the technical details folded away, no cycle, assigned to the user, then push each change as a bookmark named after the ticket's auto-generated git branch. Use ONLY when the user invokes /ticket, with jj change ids or bare for the change this conversation created.
---

# ticket

Turn jj changes into Linear tickets plus pushed branches. Input: one or more jj
change ids (e.g. `/ticket pnqsvuml utlnmzkl`). Each ticket gets a description
in the shape that `## Description` gives.

Invoked bare (`/ticket`), the target is the change this conversation just
created, normally the one `/daniel` parked on a `handoff/` bookmark. If this
conversation created no change, ask which one instead of guessing.

## Defaults

Read `${SKILLS_AGENTS_PRIVATE:-$HOME/.config/skills-agents}/ticket.md`. It
gives the Linear team id and key, the assignee and the branch glob. If the file is
missing, ask Daniel for the team once and use assignee `"me"`. Never set a
cycle, even if that file names one.

## Description

Write it from the change's diff and from this conversation. Two parts, in
this order:

1. **Summary.** 2 to 4 short sentences, under 60 words, in plain English.
   Say what a user sees go wrong or what now works, and why it matters.
   Write for someone who uses the app but does not read code. No file names,
   field names, function names, rule codes, commit ids or numbers that need
   context.
2. **`+++ Technical details`**, closed by a lone `+++` line. Everything else
   goes here: the change list, worked examples with numbers, side effects,
   out of scope, repro steps, commits, files, tests and QA clone ids.

Nothing technical goes above the `+++` line. Use `##` headings inside the
folded part only when it has more than one topic.

Example:

```
Cost Approach totals could be $1 off from Spark. We rounded each cost line
and then added them. Spark adds first and rounds once. Now both show the same
cost-new on the screen, the PDF and the export.

+++ Technical details

## Changes

- Each rate goes to whole cents. The cents of all lines of a structure are
  added, and the sum is rounded once, half away from zero.
- `depreciated_cost_dwellings` and `estimated_total_cost` use the
  once-rounded cost-new.

## Out of scope

- Several buildings, because Spark has no rule for them.

## Agent notes

- Commits: `ukvxukot` adds `costRounding.ts`; `sopzoyzu` adds
  `deriveStructureCost`.
- Tests: costApproach unit tests pass. Typecheck and lint pass.

+++
```

## Flow

0. **Pin the repo root.** The shell's cwd resets between tool calls and may
   land in a subdirectory, so resolve the root once and pass it explicitly to
   every `jj` call from then on:
   ```bash
   REPO=$(jj root)
   ```
   Run every subsequent `jj` command as `jj -R "$REPO" ...`. Never hardcode a
   repo path. `jj root` names the default checkout, which goes stale once a
   workspace rewrites its commits; if a command fails with "The working copy is
   stale", rerun it with `--ignore-working-copy`. Never run
   `jj workspace update-stale`: it rewrites files other agents are using.
1. **Describe first.** Run `jj -R "$REPO" git fetch`. For each change id,
   inspect its branch commits with a template that never prints a blank line,
   so an empty result is unmistakable:
   ```bash
   jj -R "$REPO" log -r 'main@origin..<id>' --no-graph \
     -T 'change_id.short() ++ " | " ++ if(description, description.first_line(), "(no description)") ++ "\n"'
   ```
   - No lines at all → the id has no commit outside `main@origin`. Run
     `jj -R "$REPO" log -r '<id>'` to see what it is and stop with that
     finding; do not guess a title.
   - Any commit shows `(no description)` → read its diff
     (`jj -R "$REPO" diff -r <commit> --git`) and describe it before anything
     else:
     ```bash
     jj -R "$REPO" describe -r <commit> -m "<one-line summary of the diff>"
     ```
     jj refuses to push undescribed commits, so this is not optional. `describe`
     touches only the message; it is allowed.
2. **Check for a handoff bookmark.** A change still parked by `/daniel` carries
   a `handoff/<name>` bookmark instead of a proper one:
   ```bash
   jj -R "$REPO" log -r '<id>' -T 'bookmarks ++ "\n"' --no-graph
   ```
   If a `handoff/<name>` bookmark is on it, ticketing supersedes the park: step 8
   deletes it after the push. Left in place, it would mark already-ticketed work
   as still parked and waiting for `/daniel-integrate`.
3. Load tools if needed:
   `ToolSearch("select:mcp__claude_ai_Linear__save_issue")`.
4. Do not fetch or set a cycle.
5. Title: one commit → that commit's first line. Several commits → write a
   plain one-line title that covers all of them.
6. Create one ticket per change with `save_issue` (team, assignee, title,
   description; nothing else). Pass real newlines in the description, not
   `\n`. Take `gitBranchName` from each response.
7. Prefix each commit's description with the ticket id if it lacks one:
   `jj -R "$REPO" describe -r <commit> -m "[<KEY>-NNNN] <existing first line>"`.
8. Bookmark, rebase onto `main@origin` if needed, and push:
   ```bash
   jj -R "$REPO" bookmark create <gitBranchName> -r <id>
   ```
   If `jj -R "$REPO" log -r 'main@origin ~ ::<id>' --no-graph -T 'change_id'`
   prints anything, `main@origin` is not an ancestor of the tip:
   - `jj -R "$REPO" rebase -b <id> -d main@origin`. If the rebase leaves a
     conflict, stop before the push and report the conflicted commits.
   - Typecheck the rebased tip in a throwaway workspace:
     `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/new-workspace.sh" ticket-check-<id> <id>`,
     run the typecheck command from the repo profile's `notes.md` there, then
     `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/cleanup-workspace.sh" ticket-check-<id>`.
     If the typecheck fails, stop before the push and report the errors.
   ```bash
   jj -R "$REPO" git push --bookmark <gitBranchName> [--bookmark ...]
   ```
   `--bookmark` already pushes new bookmarks; `--allow-new` does not exist in
   this jj version. If step 2 found a handoff bookmark on this change, delete
   it now: `jj -R "$REPO" bookmark delete handoff/<name>`.
9. Confirm with `jj -R "$REPO" bookmark list --tracked '<branch glob>'`, or
   name each `gitBranchName` when the defaults give no glob.

## Report

One table: change id, ticket id, bookmark, merge request URL from the push
output, whether a handoff bookmark was deleted, and whether it was rebased
onto `main@origin`.

Then run `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-verify/verify.sh" list`.
Run `verify.sh stop <port>` yourself for every server whose workspace this
run ticketed, then `verify.sh stop --gone`. In one line, name the servers
still running. Never ask Daniel to stop a server.
