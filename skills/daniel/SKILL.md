---
name: daniel
description: Orchestrate the implementation of a feature, the fixing of a bug, or other code that will be committed, using the impl and jj agents. Use when the user invokes /daniel with a description or a path to a markdown file.
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

   Always run it exactly as written, with no other arguments. A branch,
   bookmark, or ticket name in the request is context for the agents, not a
   base revision. If you think a different base is necessary, ask Daniel first,
   never decide it yourself.
3. Spawn the `impl` agent, handing it the workspace directory and the full request. Relay its report (result, modified files, and its diff hunk for every modified file, verbatim and complete) to Daniel and wait for approval. Never trim or summarise the hunks, and keep the ```diff fences and the leading space/`-`/`+` on every line so the terminal colours them.
4. If Daniel does not approve: send the feedback to the same running `impl` agent via SendMessage. It already has the file context. Spawn a fresh `impl` agent only if the previous one is dead or Daniel asks for a clean take.
5. If Daniel approves: spawn the `jj` agent, handing it both the impl workspace directory and the original workspace directory (this conversation's cwd). It runs all jj commands from the original workspace so that workspace never goes stale. It plans only, it commits nothing. Relay its plan (commit vs squash vs split, target revisions, files, messages) to Daniel and wait for approval.
6. If Daniel rejects the plan: send the feedback to the same running `jj` agent via SendMessage. It replans and reports again, still without touching the repository.
7. If Daniel approves the plan: tell the same `jj` agent to execute it. Relay its report of what was committed or squashed and wait for approval.
8. If Daniel rejects the executed result: send the feedback to the same running `jj` agent. It undoes and redoes its own commits.
9. If Daniel approves the commits: tell the same `jj` agent to clean up (verify the workspace is clean, then delete it). Relay confirmation and finish by deleting the workspace folder.
