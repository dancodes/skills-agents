---
name: fix-conflict
description: Resolve every jj conflict in a stack of commits bottom-up, squash each fix into the conflicted commit, check the stack tip, and push. Use when the user invokes /fix-conflict, or says "fix conflict", "fix the conflicts", or "resolve conflicts" in a jj repo.
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: >-
            python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/push-needs-check.py"
---

# /fix-conflict

Input: `/fix-conflict [bookmark or change id]`. Without one, the stack is the
conflicted commits that are yours: `conflicts() & mine() & mutable()`.

Fix it fully. Every step runs, however small the fix looks.

## Steps

1. `jj git fetch`. Name the stack's tip and its bookmarks. Record `@`:
   ```
   jj log -r '@' --no-graph -T 'change_id.shortest() ++ "\n"'
   ```
2. Take the earliest conflict: `jj log -r 'roots(conflicts() & <stack>)'`.
3. `jj new <conflicted-change-id>`, then `jj resolve --list` for the files.
4. Edit the markers out. Keep both sides unless one side deleted the file:
   then the file stays deleted. Dropping a side silently removes a change.
5. `jj squash -u` into the conflicted commit. The tripwire hook then lists
   the conflicts left. That list is your next work, not a reason to stop.
6. Repeat from step 2 until `jj log -r 'conflicts() & <stack>'` is empty.
7. Check at the tip: `jj new <tip>`. Run the typecheck and the lint of every
   file you resolved, in the foreground. Do not run tests. Take the commands
   from the repo profile's `notes.md`
   (`"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/repo-profile.sh" dir`)
   or the repo's CLAUDE.md. Frontend, from `frontend/`: `yarn generate-api`
   (the generated client is gitignored and goes stale after a rebase), then
   `yarn typecheck && yarn lint`. Use package.json scripts only. Never `npx`
   or `node_modules/.bin/<tool>`: hooks block both.
8. A check fails: fix it in the working copy, then
   `jj squash -u --into <owner> <path>`, where the owner is the stack commit
   that last touched that file. Rerun step 7.
9. Push the stack's own bookmarks only: `jj git push -b <bookmark>`, in its
   own Bash call. A hook denies the push until a check passes after the last
   edit or jj rewrite, so a squash in step 8 means you rerun step 7 first.
   Never push a bookmark the user did not name or does not own.
10. Put `@` back: `jj edit <recorded @>` if it still exists, else leave it on
    the tip.

## Report

One line per resolved commit: change id, files, which side won. Then the
check commands and their results, and the pushed bookmarks. In one line, name
any other conflicted bookmark you left alone.
