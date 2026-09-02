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

1. Load tools if needed:
   `ToolSearch("select:mcp__claude_ai_Linear__save_issue,mcp__claude_ai_Linear__list_cycles")`.
2. Fetch the current cycle once.
3. For each change id, read its branch commits:
   ```bash
   jj log -r 'main..<id>' --no-graph -T 'description.first_line() ++ "\n"'
   ```
   One commit → the title is that commit's first line. Several commits → write a
   plain one-line title that covers all of them.
4. Create one ticket per change with `save_issue` (team, assignee, cycle, title;
   nothing else). Take `gitBranchName` from each response.
5. Bookmark and push, all in one go:
   ```bash
   jj bookmark create <gitBranchName> -r <id>
   jj git push --bookmark <gitBranchName> [--bookmark ...]
   ```
   If push refuses a new bookmark, retry with `--allow-new`. If that flag is
   unknown, plain `--bookmark` already handles it.
6. Confirm with `jj bookmark list --tracked 'glob:danielsorichetti/tf-*'`.

## Report

One table: change id, ticket id, bookmark, merge request URL from the push output.
