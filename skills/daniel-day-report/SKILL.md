---
name: daniel-day-report
description: Build and publish Daniel's day report — a five-tab Artifact page (Day, Waste, Tasks, Open work, Fixes) on his Claude sessions, jj commits, GitLab MRs and Linear tickets of one day, with Opus agents that find the bottlenecks and rank fixes. Use when Daniel invokes /daniel-day-report, or asks to analyze his day, report on his day, or see where his time went.
---

# daniel-day-report

One run makes `~/dayreports/<date>/` and publishes a new Artifact for the
day. Scripts collect and draw the data. Opus agents read the sessions and
write the judgement. The page template is fixed: never hand-edit the page.

`<SKILL>` is `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-day-report`.
Run the scripts with `python3 -B` from any folder (not `-I`: they import
`common.py` beside them).

## Profile

`${SKILLS_AGENTS_PRIVATE:-$HOME/.config/skills-agents}/day-report.json`
holds the time zone, the output folder, the GitLab user and project id, the
jj repos, the ticket pattern, the paths the fix list may name, and the
headless Chrome path. No profile: stop and ask Daniel for one.

## Steps

1. **Collect.** Date is `today` (default), `yesterday` or `YYYY-MM-DD`, in
   the profile time zone.
   ```bash
   python3 -B <SKILL>/scripts/collect.py <date>
   ```
   It writes `digests/`, `sessions_raw.json`, `jj.json`, `gitlab.json`,
   `groups.json` and the agent prompts in `prompts/`. It skips this session.
   Read its `ERROR` lines: a jj or glab fail leaves that data empty. Report
   it, do not stop.

   Run again on a day that already has `analysis/` (for example, to take in
   the rest of today): it keeps the old groups and writes
   `prompts/missing.md` for the new sessions only. Run step 3 for
   `missing.md` alone, then steps 4 to 7.

2. **Linear.** Load `mcp__claude_ai_Linear__list_issues` with ToolSearch.
   Call it with the arguments that `collect.py` printed:
   `assignee: "me"`, `updatedAt: <day start, UTC>`, `limit: 100`,
   `fields: ["id","title","status","createdAt","updatedAt","startedAt","completedAt","canceledAt"]`.
   Follow `cursor` while `hasNextPage` is true. Write
   `{"issues": [...all rows...]}` to `<day dir>/linear.json` with the Write
   tool.

3. **Analysis agents.** In ONE message, start one background `Agent` for
   each `prompts/<group>.md` except `wrap.md`: `subagent_type:
   "general-purpose"`, `model: "opus"`, description `Day report: <group>`,
   prompt `Read <day dir>/prompts/<group>.md and do exactly what it says.`
   Each writes `analysis/<group>.json`. Wait for all of them. Do not read
   their transcripts.

4. **Wrap agent.** When every `analysis/<group>.json` exists, start one
   background `Agent` (`general-purpose`, `opus`) with the prompt
   `Read <day dir>/prompts/wrap.md and do exactly what it says.` It writes
   `tasks.json` (ranked fixes) and `open.json` (open work).

5. **Build.**
   ```bash
   python3 -B <SKILL>/scripts/build.py <date>
   ```
   It merges everything into `report.json` and writes `page/index.html`.
   Each `WARN` names a gap. A missing or broken analysis file: run that
   group's agent again, then build again. A bad field value falls back to a
   safe default, so a few warnings need no rerun.

6. **Check.**
   ```bash
   python3 -B <SKILL>/scripts/check.py <date>
   ```
   It loads the page in headless Chrome, light and dark, at 1280 and 390 px.
   It fails on JS errors, empty panels and sideways scroll, and saves
   screenshots in `page/shots/`. Read `light-day.png`, `light-tasks.png` and
   `phone-day.png`. Fix the cause in the data or the template, build and
   check again. Do not publish a FAIL.

7. **Publish.** One new Artifact for each day:
   `Artifact(file_path: "<day dir>/page/index.html", icon: "chart",
   description: "Where Daniel's time went on <date>: sessions, waits, open work and ranked fixes.")`.
   To fix the same day's page later in this session, publish the same path
   again.

8. **Report** in ASD-STE100: the link, then 4 bullets — the largest loss
   (theme and minutes), the top fix (title and minutes), what is still
   open, and any data that is missing (collect errors, build warnings). Say
   that the page is private until Daniel shares it.

## Rules

- Read-only on every repo, MR and ticket. The report changes nothing but
  its own day folder.
- Never put the output in `/tmp`: a restart deletes it.
- Never start a local server for the page. Use `check.py`.
- The analysis agents run on Opus. Do not change the model to save cost.
- A jj conflict message from a hook during the run is not a finding unless
  `jj.json` or a session shows the conflicts.

## Files

| File | Job |
|---|---|
| `scripts/collect.py` | session digests and timing, jj, GitLab, agent groups and prompts |
| `scripts/build.py` | `report.json` with KPIs, axis, findings, MR stacks; assembles the page |
| `scripts/check.py` | headless Chrome checks and screenshots |
| `scripts/common.py` | profile, day bounds in the profile time zone, shared lists |
| `prompts/analyst.md` | analysis agent prompt template |
| `prompts/wrap.md` | fix list and open work prompt template |
| `template/` | `body.html`, `page.css`, `page.js`; the page reads only `REPORT` |

The page uses `../daniel-artifact/base.html` for its head, theme switch and
chips. Themes, bottleneck kinds and phase kinds are fixed lists in
`common.py`. The display names of kinds and phases are in `template/page.js`
(`KIND`, `PHN`); change both together.

Session timing: work is the union of main-thread turns and subagent
activity. A gap of 1 min or more between them is "stopped". A wake-up 60
min or more after the last prompt with no new prompt (a killed background
task) is not counted.
