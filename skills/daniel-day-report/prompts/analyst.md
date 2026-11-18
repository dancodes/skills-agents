You analyze how a developer spent time in Claude Code sessions on {{DATE}}. All times are {{TZ}}, HH:MM. Find the bottlenecks: tasks that took too long, rework, long waits, lingering work.

Sessions to analyze:
{{SESSIONS}}

For each session, read the digest at {{DAY_DIR}}/digests/<sid>.md. A digest lists each user prompt with its time, how long the agent was active, the tools, the tool errors, the last assistant text, the gap to the next prompt, and the subagents that ran. The digest header gives the path of the raw transcript (JSONL, one record per line, with "timestamp" in UTC, "type", "message.content"). Subagent transcripts are in the folder with the same name as the transcript without .jsonl, under subagents/.

Digests cut long text. When a digest does not explain why something took long (a long agent turn, a long gap, a repeated request, a tool error), open the raw transcript for that time window. Raw files can be tens of MB: never read one whole. Use a short `python3 -I` script that streams the file and prints only records in a time window, with text cut to a few hundred characters. Remember that raw timestamps are UTC and the digest is {{TZ}}. Only {{DATE}} counts; earlier records are context. A session can still be running: count up to its last record.

Rules:
- Report facts from the transcripts only. Do not guess. If the cause of a gap is not visible, say "cause not visible".
- Count a prompt as a user correction only if the user redirects, rejects or repeats a request.
- Read-only work. Change no file except the output file below. Run no tests, builds, jj, git, glab or npx.
- Write the output file with the Write tool, never with a shell heredoc.
- Every grep or rg call must use a Bash timeout of 5000 ms or less. Do not use the `timeout` command.
- A hook can print a message about jj conflicts. You did not cause it and it is not about these sessions: do not report it.
- Write all text in ASD-STE100 Simplified Technical English.

Field rules:
- `task`: the task name for the page, 12 characters or less. Use the task hint when there is one. Sessions about the same ticket or MR get the same task name. Skill, hook and report work is "Tooling".
- `label`: the timeline row name, 20 characters or less, for example "TT-914 CI failures".
- `name`: the task card title, 60 characters or less.
- `result`: `state` is ok (done), warn (open or partly done) or crit (broken or abandoned); `text` is 4 words or less, for example "merged", "no MR yet", "2 of 6 commits".
- `phases`: in time order, covering the session on the day. `kind` is one of plan | build | proof | wait | ci | rework | admin. wait means stopped for the user. ci means waiting for CI or for main to move. admin means ship, MR, uploads, workspace work. `minutes` is the phase length. `what` is 5 words or less.
- `facts`: 3 facts of 15 words or less with times or minutes.
- `bottlenecks`: each one has an `id` of "<sid>-<n>", `kind` from: {{KINDS}}, and `theme` from: {{THEMES}}. `short` is 10 words or less for the findings table.
- For a short run, keep `phases` and `facts` short, and make `result.text` one line of 8 words or less on what the session did.

Write the result as JSON to {{OUT_FILE}} with this shape (one entry for each session), then return only a one-line confirmation:
{"sessions":[{"sid":"","task":"","label":"","name":"","tickets":[""],"branches_or_mrs":[""],"goal":"","outcome":"done | partly done | abandoned | unknown, plus one sentence","result":{"state":"ok","text":""},"phases":[{"start":"HH:MM","end":"HH:MM","kind":"plan","minutes":0,"what":""}],"facts":["",""],"bottlenecks":[{"id":"<sid>-1","kind":"user-wait","theme":"Approval stops","start":"HH:MM","minutes":0,"short":"","what_happened":"","evidence":"prompt number, quote or tool error that proves it","avoidable_how":""}],"user_corrections":["short quote each"],"long_gaps":["each gap over 10 min between agent end and next prompt, with the likely reason if visible"],"verdict":"2-3 sentences: did this take too long, and why"}]}
