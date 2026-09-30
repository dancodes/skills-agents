---
name: daniel-review
description: Review pushed jj branches, one background review agent per branch, each publishing a light mode findings page.
disable-model-invocation: true
---

# /daniel-review

Input: `/daniel-review <bookmark> [<bookmark> ...] [focus]`. A bookmark is a
branch name on `origin`, e.g. `users/cstoltman/adu-wrap-up-ux-demo`. Text after
the bookmarks is the focus; pass it verbatim to every agent.

You are the orchestrator. You fetch, spawn and relay. The review agents read
the code.

## Steps

1. **Fetch and list.** In one Bash call, from the repo root:
   ```bash
   cd "$(jj root)" && jj git fetch -b <bookmark> [-b <bookmark> ...] && \
   for b in <bookmark> ...; do echo "== $b"
     jj log -r "::$b@origin & ~::trunk()" --no-graph \
       -T 'change_id.short(8) ++ " " ++ description.first_line() ++ "\n"'
     jj diff --stat -r "::$b@origin & ~::trunk()" | tail -1
   done
   ```
   Done when every bookmark lists at least one commit. A bookmark with none is
   merged or misspelled: tell Daniel and drop it.
2. **Spawn one review agent per bookmark**, all in one message:
   `subagent_type: general-purpose`, `run_in_background: true`, the brief
   below with every `<placeholder>` filled. The title is 2–4 words naming the
   branch topic and ending in "Review".
3. **Tell Daniel what runs**: one line per bookmark with its commit count and
   diff stat.
4. **Relay each report as it arrives**: the page URL, then the findings list
   (severity, file:line, one line each), verbatim from the agent.

## Review agent brief

```
Review the code on jj bookmark `<bookmark>@origin` in repo <repo root>. It is
already fetched. Then publish the review as a light mode HTML Artifact.

Scope: the commits in revset `::<bookmark>@origin & ~::trunk()`:
<one line per commit: change id and title>
Diff stat: <stat line>.
Read the diff with `jj diff --git -r '<revset>'`, or per commit with
`jj diff --git -r <change id>`. Read whole files at the tip with
`jj file show -r <tip change id> <path>`.
Focus from Daniel: <focus, or "none">.

This is a reading review. You prove each finding by tracing the code path and
quoting the lines. Run zero tests, typechecks, linters or scratch scripts: not
in the repo, not in a copied or exported tree, not in the scratchpad. Your
tools are jj log, jj diff --git, jj file show, grep and Read. The repo, its
working copy and its bookmarks stay exactly as you found them.

1. Read every CLAUDE.md from the repo root down to each touched directory, and
   the docs they point at for the touched code. Apply their rules to the diff.
2. Read sibling code in the touched directories. Judge whether the new code
   follows the existing patterns and reuses the existing helpers.
3. Hunt for:
   - correctness bugs and broken edge cases;
   - data loss: saves that clear or delete data the user did not touch;
   - frontend and backend drift: field names, codes, save and load round trips;
   - schema changes missing from the production changelog or the test schema;
   - duplicated logic that an existing helper already covers;
   - over-engineering: an abstraction with one user, config for a fixed value;
   - comments (the team writes none), and docs the change made stale;
   - WIP leftovers, demo or debug code, unrelated changes;
   - missing tests, above all for the bugs you found.
4. Trace every finding against the code at the tip before you keep it. Drop
   what you cannot trace. Each kept finding has a severity (High, Medium, Low,
   Nit), a file:line, and the quoted lines.

Artifact:
- Load the `findings-report` skill and follow it.
- Light mode only: delete the template's two dark mode blocks (the
  `@media (prefers-color-scheme: dark)` block and the
  `:root[data-theme="dark"]` block) and set `color-scheme: light` on `:root`.
- Title: "<title>". Icon: "code".
- Page text in ASD-STE100 Simplified Technical English: short sentences, one
  idea each, active voice.

Final reply: the artifact URL, then one line per finding: severity, file:line,
what is wrong. Nothing else.
```
