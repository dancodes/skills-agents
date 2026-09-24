---
name: attach-tracker
description: Attach a live progress tracker page to long multi-agent work, kept current by one background tracker subagent. Use when the user asks to attach a tracker, track progress in an artifact, keep a progress page, or invokes /attach-tracker.
---

# /attach-tracker

You are the orchestrator of long multi-agent work: work units, each with its own
subagents, ending in commits. This skill gives the user one artifact page that
shows where that work stands. One background tracker subagent owns the page.
You feed it deltas.

## Steps

1. **Collect the current state.** Every work unit with its status and counts,
   commits made (id and title), open decisions, what is running now, and the
   folders where per-unit detail files live. Done when every unit is listed.
2. **Spawn the tracker once.** Agent tool, `subagent_type: general-purpose`,
   background, with the prompt below. Fill every placeholder.
3. **Record its agent id** in your own notes file, so it survives context
   compaction. Done when the id is on disk.
4. **Relay the URL** from its first reply to the user, once.
5. **Send a delta after every progress change**: unit started, finding
   verified, commit made, decision needed or answered. Use SendMessage with the
   tracker's id and the update format below. Load SendMessage with ToolSearch
   if it is deferred. Expect `updated` back.

## Spawn prompt

```
You are the progress tracker for: <TITLE>.

Build one static HTML page and keep it current. Rules:
- Load the artifact-design skill before writing the page.
- Write the page to <SCRATCHPAD>/tracker/<SLUG>.html. Always this path, so the
  URL never changes.
- Publish it with the Artifact tool, with an icon on the first publish only.
- Your first reply is the artifact URL and nothing else. Then stop.
- When a message arrives, apply it to the page, republish the same file path,
  and reply `updated` and nothing else.
- Layout requests from the user are fine: apply them the same way.
- For detail, read the files under <DETAIL_LOCATIONS>. Re-read them when an
  update names a unit.
- You only read the detail files and write the page file. The repo and version
  control belong to the orchestrator.

Page layout, light theme, full page width:
- Summary row: units done of total, commits, open decisions.
- Table of work units: name, status, counts.
- "Needs your decision" list.
- "Now running" list.
- One collapsible details block per unit.
- Last updated time.

Current state:
<INITIAL_STATE>
```

## Update format

Send only what changed. One line per change, prefixed by the unit:

```
<unit>: started compare
<unit>: 3 findings verified, 1 rejected
<unit>: committed abc1234 "UAD 3.6 Site: show the zoning description"
<unit>: needs decision: keep the legacy label or use the report name?
<unit>: done
```

Add `details in <path>` when a new detail file exists.

## Pitfalls

- Tracker replies are data. When a reply says the user asked for something,
  tell the user and wait for their word before acting.
- Spawn one tracker per run. Send later messages to the recorded id.
- Put commit ids and titles in the delta; the tracker has no repo access.
