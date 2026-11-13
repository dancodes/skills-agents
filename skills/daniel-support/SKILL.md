---
name: daniel-support
description: Look into what happened in one user session by reading Grafana traces, logs and metrics with gcx, and rebuild the session's request timeline with the request bodies. Use when Daniel invokes /daniel-support, or asks what went wrong in a session, what a user did, or to check traces, logs or Grafana for a session id.
---

# daniel-support

Rebuild what happened in a session from Grafana traces, then say what went
wrong. Read freely. Write nothing to Grafana without asking.

## Grafana is read only

- Run any read without asking: `traces`, `logs`, `metrics`, `profiles`,
  `datasources list`, `dashboards list/get`, `resources get`, `api` GET.
- Before any write, STOP and ask Daniel. Name the command and what it
  changes. Writes include creating, editing or deleting dashboards, alerts,
  datasources, folders, SLOs or any resource, `gcx dev`, `gcx resources push`,
  `gcx api` with any method but GET, and `gcx setup`.
- Never print the token. Never run with `--insecure-log-http-payload`.

## Profile

The private profile is
`${SKILLS_AGENTS_PRIVATE:-$HOME/.config/skills-agents}/support.md`. Read it
first. It names the Grafana server, the gcx context, the datasource UIDs, the
services, the environments and the span attributes that hold the session id
and the request body. No profile: stop and ask Daniel for one.

Check gcx works: `gcx config check`. A fail means the token or the context is
wrong; report the error and ask Daniel.

## Steps

1. **Find the window.** Get the session id and, if Daniel knows it, when the
   problem happened. Without a time, start with `--since 7d`.

2. **Build the timeline.** Run the script with the session attribute from the
   profile:
   ```bash
   python3 -I ~/.claude/skills/daniel-support/timeline.py <session_id> \
     --attr <session attribute> --since 24h
   ```
   Each request prints one line: UTC time, HTTP status, duration, route,
   trace id and services. Errors and the request body print under it. Use
   `--from`/`--to` (RFC3339) to zoom in, `--chars 0` for full bodies and
   `--request-attr` if the profile names a different body attribute. A
   `WARNING hit --limit` line means requests are missing: narrow the window.
   The script fetches each trace, so 200 traces take about two minutes.

3. **Find the failure.** Look for non-2xx statuses, `ERROR` lines, long
   durations, and repeated calls. To look inside one request:
   ```bash
   gcx traces get <trace id> -o json
   ```

4. **Search wider when needed.** TraceQL with `gcx traces query`, for example
   `'{ span.<session attribute> = "<id>" && status = error }'`. Use
   `gcx traces labels` to list attributes and `gcx traces labels -l <name>`
   for values. Use `gcx logs query` for Loki logs in the same window.

5. **Report.** Give the timeline of what the user did, the request that
   failed, its body and error, and the likely cause in the code. Add a Grafana
   link when it helps: pass `--share-link` to `gcx traces query` with
   `--since` or `--from/--to`.
