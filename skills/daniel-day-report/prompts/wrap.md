You write the last two parts of Daniel's day report for {{DATE}}. All times are {{TZ}}, HH:MM. The data was collected at {{NOW}}.

Read these files in {{DAY_DIR}}:
- analysis/*.json: one analysis for each Claude session (goal, outcome, result, phases, bottlenecks with minutes, verdict).
- sessions_raw.json: session timing (minutes since local midnight), titles, first prompts.
- gitlab.json: GitLab events of the day and Daniel's open MRs.
- jj.json: Daniel's commits of the day.
- linear.json: Daniel's Linear tickets updated since the day started.
- digests/<sid>.md: open one only when the analysis does not explain something.
- {{PREV_TASKS}}: the task list of the last report ("none" means there is none). Do not repeat a fix that is already in place. If today's data shows that an applied fix is not complete, name the gap.

Rules:
- Read-only work. Change no file except the two output files. Run no tests, builds, jj, git, glab or npx. Create no tickets.
- Write the output files with the Write tool, never with a shell heredoc.
- Every grep or rg call must use a Bash timeout of 5000 ms or less. Do not use the `timeout` command.
- A hook can print a message about jj conflicts. You did not cause it: do not report it unless jj.json or a session shows the conflicts.
- Write all text in ASD-STE100 Simplified Technical English.

1. Priority tasks that cut Daniel's time and process waste. Look at the real skill and hook files under {{FIX_PATHS}} so that each task names the real file and the real rule to change. Rank by minutes saved for each unit of effort. At most 12 tasks. A task is a tool change or a habit change. Write compact JSON to {{DAY_DIR}}/tasks.json as a bare array:
[{"rank":1,"title":"10 words or less","type":"tool|habit","saves_min":0,"evidence":"minutes lost on {{DATE}} with session id and time","change":"the exact change","file":"real path, or empty for a habit","effort":"S|M|L","check":"how to check that it worked"}]

2. Open work at {{NOW}}: what is not finished. Include tickets with no MR, MRs not approved or with conflicts, stale MRs, sessions still running, and changes not tested. At most 14 items, the most urgent first. Write JSON to {{DAY_DIR}}/open.json as a bare array:
[{"item":"TT-898 or !7825 (TT-904)","state":"ok|warn|crit","flag":"4 words or less","detail":"one or two short sentences with times"}]

Return only a one-line confirmation.
