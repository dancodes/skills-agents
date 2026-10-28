---
name: daniel-duo
description: Investigate one bug with two independent agents, a quick fixer and a root cause hunter, then have a writer merge both into one write-up.
---

# /daniel-duo

Input: one issue. It can be a bug report, a ticket, or a section of a doc
(give the path and line range). Pass along any shared context the issue
depends on, such as a note that names a cause it shares with other issues.

Two agents look at the same issue from opposite ends. The fixer finds the
cheapest change that makes the bug stop. The hunter asks why the bug can exist
at all. A writer weighs both and writes the findings. The reader then chooses:
ship the patch, do the refactor, or patch now and refactor next.

The caller decides how to run the agents, for one issue or for many. This
skill only says who does what and what each one hands back.

## Rules for both investigators

- Run on Opus at xhigh effort.
- Work independently. Neither one sees the other's output.
- Stay read-only. They return a diff or a design and leave the code as they
  found it. Other agents may share the working copy, and the writer compares
  both before anything lands.
- Confirm every claim in the issue against the current code first. The issue
  text can be stale.

## 1. Fixer

Goal: the smallest correct change that stops the bug. This is usually what the
issue recommends.

Trace every caller of the function it would change. One guard in a shared
function beats one guard per caller.

Returns:
1. The cause in two or three sentences, with file:line references it checked.
2. The fix as a unified diff, not applied.
3. The red test that proves it: file, test name, setup, and the assertion that
   fails today.
4. Risks, and any other known issues the fix changes.

## 2. Hunter

Goal: why this kind of bug can exist. Its output is a diagnosis and a refactor,
never a patch for this bug.

Look for accidental complexity: duplicated state, more than one source of
truth, stale copies, saves that merge or diff by hand, rows matched by
position, and effects that write data when a page opens.

Returns, with file:line references it checked:
1. Root cause: the design flaw, in a short paragraph.
2. Evidence: the code paths that show it.
3. The refactor: what changes, what goes away, and the target design.
4. Other known issues that share the root cause and would also go away.
5. Size, risk, and a landing order that names the first step.

## 3. Writer

Runs after both investigators and gets both outputs verbatim. It checks the
code (read-only) only where the two disagree, and says which one is right.

Returns one Markdown section:
- `## <id>. <title>`
- `### Cause`: two or three sentences.
- `### Straightforward fix`: what changes and where, the fixer's diff in a
  fenced block, then the red test in one or two sentences.
- `### Root cause and refactor`: the flaw, the refactor, and the other issues
  it would fix.
- `### Recommendation`: one short paragraph. Ship the quick fix, do the
  refactor, or do the fix first and the refactor next, and say why.

With many issues, the caller joins the writers' sections in order.
