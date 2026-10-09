---
name: daniel-split
description: Split one jj change into a stack of smaller commits that each land cleanly, guided by an import map of which files must land together or in order. Use when the user invokes /daniel-split, when a change is too big to review as one commit, or to check that a split plan or an existing stack lands its files in a safe order.
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: >-
            python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/forbidden-commands.py"
---

# /daniel-split

Input: the revision to split (default `@`), and optionally how the parts should
be cut. The caller is a user or another agent. A caller who asks only for a map
or a plan check gets steps 1–3 and a report; nothing is rewritten.

Every command below uses the tool by its full path:

```
"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-split/jj-import-map"
```

Written as `jj-import-map` below for short. `--help` lists its flags.

## The map

The tool reads the JS/TS and Python imports on both sides of the change and
prints three lists.

- **Hard edge** `a -> b`: `a` must land in the same commit as `b` or an earlier
  one. `imports` means `b` imports the added file `a`. `deletes-import` means
  `a` stops importing `b`, which the change deletes.
- **Soft edge**: the same shapes, but the target file is modified, not added or
  deleted. Its API may or may not have changed; only a typecheck tells.
- **Group**: files joined in a cycle. One commit must hold the whole group.
  Groups use hard edges only; `--strict` adds the soft ones.

Files that are not JS/TS or Python (JSON, CSS, config, migrations, R) carry no
edges. Place them by reading what imports or loads them. An alias import
(`~/`, `@/`, `src/`) resolves only when its path suffix matches exactly one
changed file, so an ambiguous alias shows no edge at all.

`-r <rev>` maps one change against its parent. `--from <base> -r <top>` maps a
whole stack as one diff, which is how to check an existing stack: give it a plan
with one entry per commit, oldest first.

## 1. Map

```
jj-import-map -r <rev> --json <scratchpad>/graph.json
```

For a large change, read `graph.json` instead of re-running the tool.

## 2. Plan

Write `<scratchpad>/plan.json`: a list of parts in landing order, oldest first.

```
[{"message": "<one-line commit message>", "files": ["frontend/src/a.ts", "..."]}, ...]
```

Paths are relative to the repo root, as `jj diff --summary` prints them. The
tool reads only `files`. Each part carries one idea a reviewer can read alone,
and every group sits whole inside one part.

## 3. Check

```
jj-import-map -r <rev> --plan <scratchpad>/plan.json
```

The plan is done when this exits 0 and every `soft` line it prints is either
fixed by moving a file or accepted with a one-line reason. Exit 1 means a file
is unassigned, assigned twice, not in the change, or a hard edge points
backward; fix the plan and check again.

Show the parts (message and file count each) to a human caller and wait for a
go-ahead, unless they already gave one. An agent caller that asked for the split
has given it.

## 4. Lock

```
"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-integrate/integrate-lock.sh" acquire
```

The lock `/daniel-integrate` holds, for the same reason: two runs rewriting the
same commits leave them divergent. Skip this when the run that called you
already holds it. If it fails, relay its output and stop. Release it when the
run ends, including when it ends early.

Split from the integration workspace or a plain checkout. The hooks deny
`jj split` inside `daniel-workspaces`.

## 5. Split

Record the tree you started from:

```
jj log --no-graph -r <rev> -T commit_id
```

Then, with `<rest>` starting as `<rev>`, for every part except the last:

```
JJ_EDITOR=false jj split -r <rest> -m "<message>" 'root-file:"<path>"' 'root-file:"<path>"' ...
jj log --no-graph -r 'children(<rest>)' -T 'change_id.shortest(8)'
```

The part you named keeps `<rest>`'s change id. The files left over move to its
new child, which the second command prints; that child is the next `<rest>`.
`JJ_EDITOR=false` makes any split that would open an editor fail rather than
hang. Name the last part with:

```
jj describe -r <rest> -m "<message>"
```

## 6. Verify

```
jj diff --summary --from <commit id from step 5> --to <last rest>
```

This must print nothing: the stack ends on the tree it started from. Then
`jj diff --summary -r <part>` for each part must list exactly that part's plan
files.

To back out the whole split, revert your own operations, newest first, with
`jj op revert <operation-id>` read from `jj op log`.

## 7. Green parts (only when asked)

By default only the top of the stack has to build; soft edges are left as
accepted. When the caller needs each part to typecheck alone:

```
"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/new-workspace.sh" split-check <part>
```

Run the typecheck in the path it prints, then remove it with
`jj workspace forget split-check` and `rm -rf <path>`. Forgetting the workspace
also drops its empty working-copy commit. A failing part means a soft edge was
real: move the missing file down with
`jj squash --from <later part> --into <failing part> -u 'root-file:"<path>"'`,
update the plan to match, and check that part again.

Report the parts in order, each with its change id, message and file count, and
every soft edge you accepted with its reason.
