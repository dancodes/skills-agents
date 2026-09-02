---
name: ticket
description: Create one Linear ticket per jj change (branch tip), title only, on the current cycle and assigned to Daniel Sorichetti, then push each change as a bookmark named after the ticket's auto-generated git branch. Use ONLY when the user invokes /ticket with one or more jj change ids.
---

# ticket

Turn jj changes into Linear tickets plus pushed branches. Input: one or more jj
change ids (e.g. `/ticket pnqsvuml utlnmzkl`). No description on the ticket.

## Fixed defaults

- `team`: `b1ca64d4-81a8-42fc-91b4-003d490fab39` (Truefootage)
- `assignee`: `6f5ba700-39da-43ab-963b-a91ffb91df9d` (Daniel Sorichetti)
- `cycle`: the team's current cycle, from `list_cycles` with `type: current`

If an id stops resolving, fall back to team "Truefootage" and assignee "me".

## Flow

0. **Pin the repo root.** The shell's cwd resets between tool calls and may
   land in a subdirectory, so resolve the root once and pass it explicitly to
   every `jj` call from then on:
   ```bash
   REPO=$(jj root)
   ```
   Run every subsequent `jj` command as `jj -R "$REPO" ...`. Never hardcode a
   repo path.
1. **Describe first.** For each change id, inspect its branch commits with a
   template that never prints a blank line, so an empty result is unmistakable:
   ```bash
   jj -R "$REPO" log -r 'main..<id>' --no-graph \
     -T 'change_id.short() ++ " | " ++ if(description, description.first_line(), "(no description)") ++ "\n"'
   ```
   - No lines at all → the id is not a descendant of `main`. Run
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
   If a `handoff/<name>` bookmark is on it, ticketing supersedes the park: after
   the new bookmark is pushed (step 7), delete the handoff bookmark with
   `jj -R "$REPO" bookmark delete handoff/<name>`. Left in place, it would mark
   already-ticketed work as still parked and waiting for `/daniel-integrate`.
3. Load tools if needed:
   `ToolSearch("select:mcp__claude_ai_Linear__save_issue,mcp__claude_ai_Linear__list_cycles")`.
4. Fetch the current cycle once.
5. Title: one commit → that commit's first line. Several commits → write a
   plain one-line title that covers all of them.
6. Create one ticket per change with `save_issue` (team, assignee, cycle, title;
   nothing else). Take `gitBranchName` from each response.
7. Prefix each commit's description with the ticket id if it lacks one:
   `jj -R "$REPO" describe -r <commit> -m "[TF-NNNN] <existing first line>"`.
8. Bookmark and push, all in one go:
   ```bash
   jj -R "$REPO" bookmark create <gitBranchName> -r <id>
   jj -R "$REPO" git push --bookmark <gitBranchName> [--bookmark ...]
   ```
   `--bookmark` already pushes new bookmarks; `--allow-new` does not exist in
   this jj version. If step 2 found a handoff bookmark on this change, delete
   it now: `jj -R "$REPO" bookmark delete handoff/<name>`.
9. Confirm with `jj -R "$REPO" bookmark list --tracked 'glob:danielsorichetti/tf-*'`.

## Report

One table: change id, ticket id, bookmark, merge request URL from the push
output, and whether a handoff bookmark was deleted.
