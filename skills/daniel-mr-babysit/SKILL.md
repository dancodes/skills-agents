---
name: daniel-mr-babysit
description: Watch Daniel's open GitLab MRs until they merge. Approve and set auto-merge at each MR's deadline, fix failed pipelines and conflicts through /daniel subagents, and retry stuck jobs. Use when Daniel invokes /daniel-mr-babysit, or asks to babysit, watch or land MRs by a time.
argument-hint: <MR>@<HH:MM> [<MR>@<HH:MM> ...]
---

# /daniel-mr-babysit

Watch a set of MRs in this session until every one merges, or until midnight.

## 1. Settle the input

Read the profile: `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/repo-profile.sh" dir`,
then the "Babysit" section of `mr.md` in that directory. It gives the GitLab
project, the time zone and the usernames whose notes are not reviews. No
profile, or no "Babysit" section: stop and ask Daniel.

Every MR needs a number (or URL) and a deadline time in the profile's time
zone. Take what the invocation gives. Ask for each missing MR or time, and for
a time already past today. Never guess one. The deadline is when the watch
approves the MR and sets auto-merge.

## 2. Start the watch

Pick a state directory: `/tmp/daniel-mr-babysit/<first MR>-<YYYYMMDD>`.

Start the Monitor tool with `timeout_ms: 1800000` and this command:

```
python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-mr-babysit/watch.py" \
  --project <project> --tz <time zone> --ignore <usernames, comma-separated> \
  --state <state directory> <MR>@<HH:MM> ...
```

It checks every 60 seconds and prints a line only when an MR changes. It
does the deadline work itself:

- At or after the deadline: approve the MR if it is not approved, then set
  auto-merge. It approves again after a push removes the approval.
- Before the deadline: if the MR is approved and has no notes from other
  people, set auto-merge at once.

When the monitor expires, start it again with the same command. The state
directory keeps it from repeating lines. Use `--once --dry-run` to see one
tick without approving or merging anything.

Add a one-time backup with CronCreate for each MR, one minute after its
deadline. Cron reads the machine's local time:
`date -d 'TZ="<time zone>" <HH:MM> + 1 minute' '+%M %H %d %m'`. Prompt: run
`watch.py … --once` for that MR, then confirm it is approved with auto-merge
on, and fix it if not. Delete an MR's backup once it has both.

## 3. Act on each event

| Event | Action |
|---|---|
| `failed_jobs=` lists a job | Pipeline fix, below. Do not ask. |
| `conflicts=True` | Conflict fix, below. Do not ask. |
| `open_threads=` above 0, or `comments=` goes up | Read the new notes. Ask Daniel what to do, with options and a recommendation. Never reply to or resolve a thread yourself. His chosen fix goes through the pipeline fix flow. |
| `STUCK job` | Cancel and retry it: `glab api -X POST projects/<URL-encoded project>/jobs/<id>/cancel`, then `…/retry`. A second STUCK for the same job name on this MR: ask Daniel. |
| `ERROR` | Read it. Retry once by hand. If it repeats, tell Daniel. |
| An auto-merge or approve line that says `failed:` | Find out why from the MR, then fix it or tell Daniel. |
| `state=merged` | Delete that MR's backup cron. |
| `ALL DONE` | End, below. |
| `CUTOFF` | Stop the watch and report each MR that is still open and why. |

Only one fix runs per MR. A new failure while a fix runs waits for that fix.

### Pipeline fix

Every code fix, from a failed pipeline or from Daniel's answer on a thread,
runs `/daniel` in a new `general-purpose` subagent, in the background. Give it
this prompt, filled in:

> MR !<N>, branch `<bookmark>`. <The failed jobs with their URLs, or Daniel's
> chosen fix with the thread text.>
> First find the cause: read the job log (`glab api projects/<URL-encoded project>/jobs/<id>/trace`).
> The owning commit is the newest commit in `::<bookmark> ~ ::trunk()` that
> touched the file at fault (`jj --ignore-working-copy log -r '…'`).
> Then invoke the `daniel` skill with: `<fix request> insta without explore
> without grilling based on <owning commit>`. Browser verify stays off.
> Daniel has said go and ship for every step. Do not wait for a reply. Keep the
> ship review. At ship, park with `--onto <owning commit> --squash`, then push
> `<bookmark>` and every other bookmark of Daniel's that the rewrite moved.
> Do not create a ticket.
> Report the cause, the pushed commit and the diff hunks verbatim, or only the
> file list when more than 5 files changed.

When it reports, relay the cause, the pushed commit and the hunks or file
list to Daniel. Do not wait for a reply. The watch picks up the new pipeline.

### Conflict fix

Run it in a new `general-purpose` subagent, in the background, with this
prompt:

> MR !<N>, branch `<bookmark>`, conflicts with trunk. Work only in a new
> workspace: `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/new-workspace.sh"
> babysit-conflict-<N> <bookmark>`, and run every command from the path it
> prints. `jj git fetch`, then `jj rebase -b <bookmark> -d 'trunk()'`. Then
> invoke the `fix-conflict` skill with `<bookmark>` and follow all its steps,
> push included. Leave other conflicted bookmarks alone. Last, remove the
> workspace with `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/cleanup-workspace.sh"
> babysit-conflict-<N>`. Report as the fix-conflict skill says.

Relay its report to Daniel without waiting for a reply.

## 4. Report

Write to Daniel only when an MR changes in a way that matters, an action ran, or
he must decide. On a quiet tick, write nothing. Give times in the profile's
time zone.

## 5. End

When every MR has merged, stop the monitor (TaskStop), delete every cron
from this watch (CronList, CronDelete), and show a table: MR, title, merged
at. Name any MR that missed its deadline and why.
