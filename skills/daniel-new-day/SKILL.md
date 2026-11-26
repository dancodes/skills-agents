---
name: daniel-new-day
description: Start Daniel's day in a jj repo. Sort his work from the last working days into done, pending and needs attention with jj and GitLab, abandon merged commits, rebase the rest on fresh main, then offer the push, MRs and conflict fixes. Use when Daniel invokes /daniel-new-day, asks what is done, pending or needs attention from recent days, or asks to rebase his work on fresh main.
argument-hint: "[working days back, default 2 | YYYY-MM-DD]"
---

# /daniel-new-day

The window starts N working days before today (default 2: on a Tuesday,
Friday), or at the date given. "Yesterday and Friday" is the default.

`<SKILL>` is `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-new-day`.
Run every command from the repo root.

## Steps

1. **Fetch.** `jj git fetch`. Its "Abandoned … no longer reachable" lines
   are branches GitLab merged and deleted: they go under Done.

2. **Status.** `python3 -B <SKILL>/status.py [--days N | --since YYYY-MM-DD]`.
   It only reads. It prints one verdict per branch with a commit in the
   window, with its full title and its commit subjects under it, Daniel's
   MRs merged since the window start, his open MRs outside the window, and
   the jj commands for steps 3 and 4. On an error, report
   it and stop. Never guess a verdict.

   | Verdict | Meaning | Report section |
   |---|---|---|
   | `MERGED` | MR merged into main, at this exact commit or with the same diff as its squash commit | Done |
   | `OPEN` | MR open: merge status, pipeline, open threads | Pending. Needs attention on a failed pipeline, an open thread or a conflict status |
   | `AFTER-MERGE` | MR merged, and commits came after its head | Needs attention: a new MR |
   | `NO-MR`, `UNPUSHED` | no MR for the branch | Needs attention |
   | `CLOSED`, `CHECK` | closed, merged into a branch that is not main, or changed after the merge | Needs attention: read it yourself. `CHECK` stacks stay out of the rebase (`HELD` line) |
   | `NO-BOOKMARK`, `HANDOFF` | commits with no branch, parked `/daniel` work | Needs attention |

3. **Abandon merged.** Run the `ABANDON` line, then the `FORGET` line.
   Abandon before the rebase: main holds a merged stack as one squash
   commit, so its separate commits rebased on main conflict with no real
   difference. Forget stops a later `jj git push --deleted` from
   deleting a teammate's branch on GitLab.

4. **Rebase.** Run the `REBASE` line. `--skip-emptied` drops commits that
   main already has. The guards tripwire then lists every conflict in the
   repo, old ones too; only conflicts in the rebased stacks are new. Leave
   them for `/fix-conflict`, and never `jj undo`. Done when the `-s`
   revset of the `REBASE` line resolves to no commits.

5. **Report** Done, Pending and Needs attention, one line per MR or stack:
   ticket, MR, title, what it changes, state. Daniel does not know tickets
   by number, so never give a bare `TT-NNN` or `!NNNN`:
   - Title: the MR title, else the Linear title (`get_issue`) when the
     bookmark names a ticket, else the tip commit's subject.
   - What it changes: a few plain words from the commit subjects under the
     branch line.
   Old conflicts and open MRs outside the window get one line each, with
   their title too.

6. **Offer** these in "What I need from you". Do each one only on Daniel's
   yes. Name each branch by ticket and title, as in the report:
   - Push the rebased branches: `jj git push -b <bookmark>` for each
     `danielsorichetti/*` branch that moved. Open MRs then rerun their
     pipelines. Ask for a branch that belongs to someone else on its own line.
   - `/daniel-mr` for each `NO-MR` and `AFTER-MERGE` branch.
   - `/fix-conflict <bookmark>` for each branch with a new conflict.
   - `/daniel-mr-babysit` for the open MRs that wait for approval.
   - A reply to each open thread: quote it and recommend an answer.
