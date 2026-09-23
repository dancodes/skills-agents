---
name: daniel-improve
description: Improve code that already works — measure function complexity with a real metric, cut the worst functions roughly in half, and strip jargon from comments, docstrings and identifiers, without changing behaviour or losing performance. Use when the user invokes /daniel-improve, or asks to reduce complexity, simplify functions that are too big, make code more readable, or remove jargon from a change.
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

# /daniel-improve

Input: `/daniel-improve <revision or file paths> [what to focus on]`.

This is for code that already works. It never changes behaviour. It measures how
big the functions are, cuts the worst ones, and takes the jargon out of the
words around them.

You are the orchestrator. Prefix every message you send with `[orchestrator]`.
The orchestrator does not explore files, read the code, or do the work itself.
Its only commands are the workspace commands below. Everything else goes to the
`impl` agent and comes back to Daniel.

## What it takes as input

- **A jj revision** (`/daniel-improve qrnppozw`) — improve the files that
  revision touches. This is the common case: a change was just landed and now
  its functions are too big.
- **File paths** — improve those files.
- **Nothing** — ask which revision or files. Do not guess.

Anything after the revision or paths is the focus: `/daniel-improve qrnppozw
also rename the abbreviations`. Pass it to the agent verbatim.

## Flow

1. Derive a kebab-case `<feature-name>` from what is being improved, ending in
   something that says this is a cleanup (`-complexity`, `-readability`).
2. Create the workspace **on top of the revision being improved**, so the
   cleanup stacks on the code it cleans:
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/new-workspace.sh" <feature-name> <revision>
   ```
   Remember that revision. Step 6 needs it. With file paths and no revision,
   run it with the feature name alone.
3. Spawn the `impl` agent with the brief below. Relay its report — the metric,
   the before/after table, every refusal with its number, the timing, and the
   diff hunk for every modified file, verbatim and complete. Keep the ```diff
   fences and the leading space/`-`/`+` on every line so the terminal colours
   them. Never trim a hunk.
4. If Daniel does not approve: send the feedback to the same running `impl`
   agent with SendMessage. It has the measurements in context; a fresh agent
   would have to re-measure.
5. If Daniel says **continue**: commit the round and keep going.
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/commit-workspace.sh" <workspace-path> "<one-line message>"
   ```
6. If Daniel approves with nothing further: land it on the revision it was
   based on.
   ```
   "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/park-workspace.sh" <workspace-path> "<one-line message>" --onto <revision>
   ```
   Add `--squash` if Daniel wants the cleanup folded into the commit it
   improves, which is usual when that commit is not yet reviewed. Without a
   base revision, park normally and offer `/daniel-integrate` or `/ticket`.

Write the message for someone who has not seen the diff: the area, a colon,
then what changed. `Backend sensitivity analysis: split `_adjust_feature` and
the search guards into their own functions, and drop jargon from the comments`.
One line, no mention of Claude, no co-author trailer.

## The brief to hand the impl agent

Give it all of this.

### 1. Measure first, and say what you measured

Never rank functions by impression. Run:

```
python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-improve/complexity.py" <files>
```

It runs ruff with every limit set to 0, so ruff reports the true score for
every function rather than only the ones already over a threshold, then maps
each score back to its enclosing function with `ast`. It adds no dependency,
reads only the files named, and writes nothing. `--isolated` keeps the repo's
own ruff config out of it, so the numbers do not move when someone edits
`pyproject.toml`.

Columns: `stmt` (PLR0915), `c901` (mccabe), `locals` (PLR0914), `branches`
(PLR0912), `returns` (PLR0911), `args` (PLR0913). `--json` for a
before/after diff, `--top N` to trim. `RUFF="uv run ruff"` to use a different
ruff than the default `uvx ruff@0.12.4`.

**Pick the metric that actually separates the functions, and say why.** On wide
code — long straight-line functions with few branches — C901 collapses: it
gives 1 or 2 to most functions and ranks nothing. Statement count spreads and
ranks everything. On deeply branching code C901 is the better rank. Look at the
spread in the table before choosing, and report the choice with the reason.

For a non-Python codebase, find an equivalent that needs no new dependency and
name it. If nothing exists, say so rather than inventing a score.

### 2. Cut the top offenders by about half

Take the largest functions by the chosen metric and reduce each by roughly 50%.

**What counts as a real cut:**

- Duplication removed. Five constructions of the same object differing in two
  fields become one construction and a small function that answers what those
  two fields are.
- One function doing two jobs becomes two functions doing one each, with the
  state between them passed as one named object — never a positional tuple of
  four things.
- A suppression deleted because the code no longer trips the rule. Removing a
  `# noqa` while the code still earns it is not a cut, it is hiding.

**What does not count:**

- Splitting a function into three that are each called once and thread state
  between them. That trades one kind of complexity for a worse one.
- Moving statements to a helper so the parent's score falls while the pair's
  total is unchanged. If this happens, **say so with both numbers.** A split
  that drops the parent 29 → 16 while adding a 15-statement helper cut one
  statement, and the honest claim is that each function now has one job and
  locals fell 14 → 6 — not that complexity fell by half.

**Refusing is a valid outcome.** If a function cannot be halved without making
it harder to read or slower, report its number, say why, and stop. A partial
honest result beats a gamed metric. Name every function you refused and what it
scored.

### 3. Never lose the performance

Cleanup runs on code someone made fast. Assume a flat-looking rewrite can cost
real time — a loop that accumulates in one pass becomes four passes over the
same list when flattened into comprehensions, and in an inner loop that shows
up.

- Find the harness or benchmark the original work used. If it is gone, rebuild
  it, and **first prove it exercises the code**: run it against the parent
  revision and against the current one, and show the gap. A harness that does
  not reproduce the original speedup measures nothing.
- Time before and after, **interleaved, at least three rounds**, so machine
  noise cancels. One before and one after is not a measurement.
- Hash the outputs and compare. Report the hash. "Results unchanged" without a
  hash is an assertion.
- If a cleanup is real but costs time, measure both, report both, and revert
  it. Say which one you reverted and what it cost.

### 4. Remove the jargon

Strip it from every comment, docstring, test name and identifier in the files
you touch.

Named offenders:

> fold / folded / folds, seam, load-bearing, surface (as a noun for an API),
> short-circuit, blast radius, carry / carries (where "has" or "copy" works),
> lands / landings / anchors, escalates, port of, twin, pinned, whole-grid,
> plumb, thread through, first-class, hydrate, reify

Plain replacements: use, help, start, about, so, but, also, has, copy, add,
make, guess.

Rules:

- Say what the code does. `_priced_grid_inputs` names nothing;
  `_inputs_with_four_priced_features` names the fixture.
- Do not rename across a contract. A telemetry span attribute, a serialized
  field, an API key and a database column are read by things outside this
  repository. Rename the local variable and leave the wire name alone — and say
  in the report that you did.
- Metaphor in a docstring usually hides a fact. `the axis the row is priced on`
  becomes `priced on the row that holds the feature`.
- Repo comment rule still applies: no comments unless the code cannot state the
  invariant itself, one short line, never a multi-line block. Run the
  `no-comments` pass before reporting and say what it deleted.

### 5. What to report

- The metric, its spread, and why it was chosen over the others.
- A before/after table of function scores, worst first, with every column.
- Each change, and why it reads better rather than merely shorter.
- Every function refused, with its number and the reason.
- The timing table, interleaved rounds, plus the harness proof and the output
  hash.
- Every wire name left alone and why.
- Which tests and lint ran, and which could not run and why (no Docker on this
  box, so `make test-src` cannot run; use `tf-run-tests` and `tf-lint`).
- Modified files, and the complete verbatim `jj diff` hunk for each.

## What this skill will not do

- Change behaviour. If a function is wrong, that is `/daniel`, not this.
- Add a dependency to measure something. Ruff is already there.
- Touch a function it did not measure.
- Reformat a file wholesale to make a diff look smaller or larger.
