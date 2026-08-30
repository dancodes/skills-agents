---
name: daniel-commit-clean
description: Audit the feature line for files a commit other than their owner modified, judge each follow-up, and squash the ones that belong back into their owner. Use when the user invokes /daniel-commit-clean, or asks to clean up the commit history, tidy the branch, or fold follow-up changes back into the commits that own them.
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: >-
            python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/forbidden-commands.py"
        - type: command
          command: >-
            python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/squash-target-check.py"
  PostToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: >-
            python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/conflict-tripwire.py"
---

# /daniel-commit-clean

Input: `/daniel-commit-clean`, optionally with `--root <revset>` if `trunk()` is not this
branch's root.

The branch is read as a sequence of commits that each own their files and add
complexity in order. A commit that modifies a file another commit owns broke that
reading: at the time it was easier to append the change than to squash it back.
This skill finds those follow-ups, decides one at a time whether each is genuine,
and folds the rest into their owners.

Some follow-ups are correct and always will be. A registry every section appends
to is modified by every section's commit and owned by none of them. The judgement
is the product here; the script decides nothing.

Prefix every message you send with `[commit-clean]`.

## 1. Refuse if this is the wrong workspace

If the working directory is under `daniel-workspaces`, this is an impl workspace.
Only the integration workspace rewrites the feature line. Its hooks would deny
every squash one at a time; refuse once instead, and do nothing else.

Parked `handoff/*` bookmarks do not block a run. They are rebased along with
everything else, and their content is unaffected. What does go stale is a set of
squash targets `/daniel-integrate` resolved *before* this run: those name commits
whose contents have moved. If a run of `handoff-owners.py` is already in hand,
re-run it after this finishes rather than squashing from it.

## 2. Take the lock

```
"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-integrate/integrate-lock.sh" acquire
```

Same lock as `/daniel-integrate`, for the same reason: two runs rewriting the
same commits leave the change divergent and every attached workspace stale. If it
fails, relay its output and stop. Release it when the run ends, including when it
ends early.

## 3. Read the report

```
python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-commit-clean/chain-followups.py"
```

Read its legend first; it defines the vocabulary below. The report has two parts.

**Aggregators.** Files touched more than the threshold, collapsed to one line
each with their count and owner. Check the *list*, not the touches: every entry
should be a file whose nature is to be appended to — a registry, a barrel file, a
fixture every section extends. If something on it is not that, ask for its cases
with a higher `--aggregator-threshold`. Otherwise say so in one line and move on.

**Cases.** One per follow-up, deepest owner first, each with the follow-up's diff
of the file. Hunks that remove or rewrite lines carry a `lines last written by`
label: that is `jj file annotate` on the follow-up's parent, and it answers the
decisive question, which is whether the owner wrote what this hunk changes. Hunks
that only add lines carry no label, because there is nothing to attribute.

## 4. Judge every case

One of three, with a one-line reason:

- **leave** — the change belongs where it is. The follow-up commit's own feature
  needed it, or the file is shared by nature. Most cases.
- **squash** — the whole touch belongs to the owner. It reads as something that
  should have been in the owner from the start, and nothing in it depends on what
  the follow-up commit introduces.
- **absorb** — part of the touch belongs to the owner. Use it when the labels show
  some hunks changing lines the owner wrote and others adding something new.
  `jj absorb` moves only what it can attribute and leaves the rest in the
  follow-up commit, which is the safe failure. A follow-up that only *adds* lines
  has nothing for absorb to attribute; there the choice is squash or leave.

A case is `squash` or `absorb` only if the content would still make sense sitting
in the owner, which is earlier in the branch. Content that references something a
later commit introduces belongs where it is, whatever the labels say.

## 5. Confirm

Present only the `squash` and `absorb` verdicts, with the one-line reason each.
The `leave` verdicts produce no command; give their count, not their list. Ask
Daniel to confirm the list before applying anything.

## 6. Apply, one at a time

In the order the report printed them, deepest owner first. Run one command, check
it, then run the next. Do not batch.

After each command:

```
jj log -r 'conflicts()' --no-graph -T 'change_id.shortest(8) ++ "  " ++ description.first_line() ++ "\n"'
jj diff --git -r <follow-up> -- <path>
```

The first finds conflicts. The second must come back empty for a `squash`, and
shorter for an `absorb`: a command that moved nothing leaves no conflict and no
trace, and is otherwise invisible.

## 7. Resolve conflicts as they happen, without asking

A squash into an ancestor can conflict in the commits between owner and
follow-up, and one command can conflict fifty. **That number is not a signal.** A
cascade is one conflict propagated forward, so one fix at the deepest conflicted
commit normally clears all of it.

```
jj edit <deepest conflicted commit>
```

Then edit the conflicted files directly, removing the markers and leaving the
content you want. jj picks that up on the next snapshot and rebases the
descendants clean. Do not run `jj resolve`: it launches an external merge tool
per file and hangs the session.

Resolve first, explain after: say what conflicted and what you chose, then
continue to the next case. No confirmation needed for a resolution.

If the correct content is genuinely undecidable, undo that one command and move
on. Read its operation id from `jj op log` and revert exactly it:

```
jj op log --no-graph -T 'id.short() ++ "  " ++ description ++ "\n"' | head
jj op revert <operation-id>
```

Then downgrade that case to `leave`, say why, and continue. `jj op restore`,
`jj undo`, `jj abandon` and `jj restore` are all forbidden and will be denied —
they act on whichever operation landed last in this shared repository, which is
usually another agent's. Never leave a conflict standing and move to the next
case: a second squash landing on top of an unresolved conflict is what turns one
fix into many.

## 8. Confirm the branch converged

Re-run the script once at the end. The follow-up count must have dropped by the
number of cases applied. Report the before and after, the verdict counts, and
every conflict resolved. Release the lock.

## What this does not check

Intermediate commits are not built, typechecked, or tested. Moving a change
backward can leave a middle commit referencing something a later commit
introduces: green at the tip, red in the middle. That is accepted here — this
branch lands as a stack read by eye, not bisected. If a commit has to be green on
its own, that is a separate tool.
