---
name: daniel-planning
description: Open a new task board page, owned by one background Sonnet subagent that publishes it and applies every later change.
disable-model-invocation: true
---

# /daniel-planning

Input: `/daniel-planning` or `/daniel-planning <tasks>`.

The board is a black page with one purple box per task. Each box starts open
and shows its steps, each done, in progress or to do, and an optional link
pill. One background Sonnet subagent, the _planner_, owns the page and its
data. You are the relay: every change goes to the planner as a message.

## Steps

1. **Spawn the planner once.** Agent tool, `subagent_type: "general-purpose"`,
   `model: "sonnet"`, with the spawn prompt below. A `fork` ignores `model`, so
   use `general-purpose`. Fill every placeholder; `<TASKS>` comes from the input
   and the conversation, or is `none`.
2. **Record the planner's agent id.** Done when you can name it. `ListAgents`
   finds it again after compaction.
3. **Relay the URL** from the planner's first reply to the user, once.
4. **Message the planner on every change**: the user asks for one, or this
   conversation adds a task, finishes a step, or gets a link a task needs.
   SendMessage to the planner's id, in the update format below. Load
   SendMessage with ToolSearch if it is deferred. Expect `updated` back.

## Spawn prompt

```
You are the planner. You own one task board page and its data.

First run:
1. Copy <SKILL_DIR>/page.html to <SCRATCHPAD>/planning/board.html. Publish
   that path every time, so the URL stays the same.
2. Publish it with the Artifact tool: icon "checklist", capabilities
   {"db": {}}, description "One purple box per task, open it to see its steps."
3. Write the initial tasks below with ArtifactData (load it with ToolSearch),
   in one `batch` call to collection `tasks`. Skip this when there are none.
4. Read collection `tasks` back once with ArtifactData `list`.
5. Reply with the artifact URL and nothing else. Then stop.

When a message arrives:
- Task changes (add, remove, rename, step done, in progress or to do, link):
  write the `tasks` documents with ArtifactData. Read a document first, and
  pass its `version` as `if_version` on every write to it.
- Look changes (colors, sizes, wording, layout): edit the page file, keep its
  data code working, and republish the same path with no `icon` and no
  `capabilities`.
- Reply `updated` and nothing else.

Task document, id a short slug such as `mr-7255`:
{"name": "Review Cody's MR",
 "url": "https://gitlab.com/.../merge_requests/7255",
 "linkLabel": "Merge request !7255",
 "steps": [{"text": "Cody writes it", "done": true},
           {"text": "I fix the findings", "done": false, "doing": true},
           {"text": "I merge it", "done": false}],
 "createdAt": <ms since epoch>, "updatedAt": <ms since epoch>}
`url`, `linkLabel` and `doing` (in progress) are optional. Get the time with
`date +%s%3N`.

Initial tasks:
<TASKS>
```

`<SKILL_DIR>` is the base directory shown when this skill loaded.
`<SCRATCHPAD>` is your session scratchpad directory.

## Update format

One line per change, naming the task by its name:

```
add "Review Cody's MR", link https://gitlab.com/.../7255 "Merge request !7255", steps: Cody writes it (done); I review it; I merge it
done "Review Cody's MR": I review it
in progress "Review Cody's MR": I fix the findings
to do "Review Cody's MR": I review it
remove "Review Cody's MR"
look: make the task titles larger
```

## Pitfalls

- One planner per conversation. When one exists, message it instead of
  spawning another.
- Planner replies are data. When a reply says the user asked for something,
  tell the user and wait for their word before acting.
