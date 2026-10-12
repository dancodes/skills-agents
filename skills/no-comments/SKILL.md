---
name: no-comments
description: Run the comment-sicko pass inline over the work just implemented. Invoked by the impl agent after implementing and before reporting back, never by a human.
---

# /no-comments

Run the final comment pass yourself, inline, before reporting the implementation.
Do not spawn another agent or wait for one. Your comments are suspect because
you wrote them.

## Scope

The files you changed in this workspace, and only the comments inside the
changed hunks. Get the list with `jj diff --summary` in the workspace
directory.

## Steps

1. Read the diff with `jj diff --git <path>` for every changed file. Hunt only
   comments inside the changed hunks: narration, banners, commented-out corpses,
   workaround sermons, and reasoning the code should express itself.
2. Delete those comments. Keep only:
   - legal or license headers;
   - non-obvious behavior forced by an external dependency, platform, vendor, or
     protocol that cannot be reshaped;
   - `// prettier-ignore`;
   - lint suppressions when the rule is faulty, pedantic, or style-only;
   - doc comments that define a public API contract;
   - issue or RFC links carrying a constraint the code cannot express.
   When unsure, delete the comment. Never rewrite one into a shorter alibi.
3. Treat `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, and similar
   suppressions as comments. If a suppression protects correctness or safety,
   delete it and flag the guilty symbol `MUST KILL`. Treat `IMPORTANT`, `do not
   remove`, `too risky`, `fine for now`, and long justifications as scent, not
   proof. Read surrounding code and grep callers before judging a flag.
4. Do not change application code merely while removing comments. Flag every
   `MUST KILL` with the exact symbol and the reshape that would make the behavior
   obvious.
5. Apply a `MUST KILL` that is a local fix inside the changed scope: a rename,
   extract, type, dead path removal, or the real API instead of a workaround.
   Fix the root cause. Leave wider fixes open for the report.
6. Never touch a file outside the scope or a comment outside the changed hunks.
   Run `jj status` in the workspace. Changes remain on disk until the
   orchestrator snapshots them.

## Report

One line back to the orchestrator, above your diff hunks: the deletion count,
anything you restored and why, the `MUST KILL` flags you fixed, the ones left
open, and comments that survived with their exception.
