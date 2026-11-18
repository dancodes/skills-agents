import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import subprocess

from common import BIG_DIGEST, KINDS, SKILL_DIR, THEMES, Clock, day_dir, load_profile, parse_ts, read_json, resolve_day, write_json

NOISE = ("<task-notification", "<local-command", "<system-reminder", "Caveat:", "<bash-")
MAX_AGENTS = 8
SHORT_CHUNK = 6
WAKE_GAP = 60


def user_text(d):
    c = d.get("message", {}).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
            return None
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return None


def is_prompt(d, txt):
    return txt is not None and not d.get("isMeta") and not d.get("isCompactSummary") and not txt.lstrip().startswith(NOISE)


def clusters(points, gap):
    out = []
    for t in sorted(points):
        if out and t - out[-1][1] <= gap:
            out[-1][1] = t
        else:
            out.append([t, t])
    return out


def union(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1] + 0.5:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def subagents(sdir, clock):
    rows, spans = [], []
    for f in glob.glob(os.path.join(sdir, "**", "agent-*.jsonl"), recursive=True):
        stamps, tools, errs = [], 0, 0
        for line in open(f, errors="replace"):
            i = line.find('"timestamp":"')
            if i < 0:
                continue
            try:
                when = parse_ts(line[i + 13:line.index('"', i + 13)])
            except ValueError:
                continue
            if clock.inside(when):
                stamps.append(when)
            if '"tool_use"' in line:
                tools += line.count('"type":"tool_use"')
            if '"is_error":true' in line:
                errs += 1
        if not stamps:
            continue
        spans += [c for c in clusters([clock.minute(s) for s in stamps], 10) if c[1] - c[0] > 0.2]
        meta = read_json(f.replace(".jsonl", ".meta.json"), {}) or {}
        rows.append(dict(start=min(stamps), end=max(stamps), type=meta.get("agentType"), desc=(meta.get("description") or "")[:90], wf="workflows" in f, tools=tools, errs=errs))
    return sorted(rows, key=lambda r: r["start"]), spans


def read_session(path, clock):
    turns, cur, title = [], None, None
    iv, prompts, open_at, last = [], [], None, None
    for line in open(path, errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "ai-title":
            title = d.get("aiTitle")
            continue
        ts = d.get("timestamp")
        if not ts or d.get("isSidechain"):
            continue
        when = parse_ts(ts)
        t = d.get("type")
        content = d.get("message", {}).get("content")
        txt = user_text(d) if t == "user" else None
        inside = clock.inside(when)
        m = clock.minute(when)
        if t == "user":
            if is_prompt(d, txt):
                cur = dict(at=when, prompt=txt.strip(), tools=collections.Counter(), errs=0, err_samples=[], texts=[], last=when, dur=0, notif=0, agents=[])
                turns.append(cur)
                if inside:
                    prompts.append(round(m, 1))
            elif cur is not None:
                if txt is not None and txt.lstrip().startswith("<task-notification"):
                    cur["notif"] += 1
                if isinstance(content, list):
                    for x in content:
                        if isinstance(x, dict) and x.get("type") == "tool_result" and x.get("is_error"):
                            cur["errs"] += 1
                            cc = x.get("content")
                            s = cc if isinstance(cc, str) else " ".join(y.get("text", "") for y in cc if isinstance(y, dict)) if isinstance(cc, list) else ""
                            if len(cur["err_samples"]) < 4:
                                cur["err_samples"].append(s[:160].replace("\n", " "))
                cur["last"] = when
            if inside and not d.get("isMeta") and not d.get("isCompactSummary") and not (txt or "").lstrip().startswith(NOISE[1:]):
                open_at = m if open_at is None else open_at
                last = m
        elif t == "assistant":
            if cur is not None:
                cur["last"] = when
                for x in content or []:
                    if not isinstance(x, dict):
                        continue
                    if x.get("type") == "tool_use":
                        cur["tools"][x.get("name")] += 1
                        if x.get("name") in ("Agent", "Task", "Workflow", "Skill"):
                            i = x.get("input", {})
                            cur["agents"].append(f"{x['name']}:{i.get('subagent_type') or i.get('skill') or i.get('name') or ''}:{str(i.get('description') or i.get('args') or '')[:70]}")
                    elif x.get("type") == "text" and x.get("text", "").strip():
                        cur["texts"].append(x["text"].strip())
            if inside:
                open_at = m if open_at is None else open_at
                last = m
                if any(isinstance(x, dict) and x.get("type") == "tool_use" and x.get("name") in ("AskUserQuestion", "ExitPlanMode") for x in content or []):
                    iv.append([open_at, m])
                    open_at = None
        elif t == "system" and d.get("subtype") in ("turn_duration", "stop_hook_summary"):
            if cur is not None and d.get("subtype") == "turn_duration":
                cur["dur"] += d.get("durationMs", 0) / 1000
                cur["last"] = when
            if inside and open_at is not None:
                iv.append([open_at, m])
                open_at = None
    if open_at is not None and last is not None:
        iv.append([open_at, last])
    return title, turns, iv, prompts


def trim_wakes(work, prompts):
    if not prompts:
        return work
    last_prompt = max(prompts)
    kept = []
    for a, b in work:
        if kept and a > last_prompt and a - kept[-1][1] >= WAKE_GAP:
            break
        kept.append([a, b])
    return kept


def digest(sid, title, proj, path, turns, subs, clock):
    mins = lambda s: f"{s / 60:.1f}m"
    lines = [f"# Session {sid} — {title}", f"project: {proj}", f"file: {path}", f"times: {clock.tz.key}, HH:MM local", ""]
    for i, u in enumerate(turns):
        if not clock.inside(u["at"]):
            continue
        span = (u["last"] - u["at"]).total_seconds()
        work = u["dur"] or span
        nxt = turns[i + 1]["at"] if i + 1 < len(turns) else None
        p = u["prompt"]
        p = p if len(p) <= 900 else p[:600] + " …[cut]… " + p[-250:]
        lines.append(f"## [{clock.hm(u['at'])}] USER PROMPT {i + 1}")
        lines.append(p)
        tl = ", ".join(f"{k}×{v}" for k, v in u["tools"].most_common(8))
        lines.append(f"- agent: active {mins(work)}, last activity {clock.hm(u['last'])} (span {mins(span)}); tools: {tl or 'none'}; tool errors: {u['errs']}; bg notifications: {u['notif']}")
        lines += [f"  - spawn {a}" for a in u["agents"]]
        lines += [f"  - error: {e}" for e in u["err_samples"]]
        if u["texts"]:
            ft = u["texts"][-1]
            ft = ft if len(ft) <= 700 else ft[:450] + " …[cut]… " + ft[-200:]
            lines.append(f"- final assistant text: {ft}")
        if nxt:
            lines.append(f"- then {mins((nxt - u['last']).total_seconds())} until next user prompt")
        lines.append("")
    if subs:
        lines.append("## Subagents active on the day")
        for s in subs:
            lines.append(f"- {clock.hm(s['start'])}-{clock.hm(s['end'])} {mins((s['end'] - s['start']).total_seconds())} {'[workflow] ' if s['wf'] else ''}{s['type']}: {s['desc']} (tools {s['tools']}, errors {s['errs']})")
    return "\n".join(lines)


def collect_sessions(profile, clock, out):
    root = os.path.expanduser("~/.claude/projects")
    me = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    pattern = re.compile(profile.get("ticket_pattern", r"\b[A-Z]{2,5}-\d+\b"))
    mr_pattern = re.compile(r"(?<![\w!])!\d{3,6}\b")
    os.makedirs(os.path.join(out, "digests"), exist_ok=True)
    rows = []
    for path in glob.glob(os.path.join(root, "*", "*.jsonl")):
        if os.path.getmtime(path) < clock.lo.timestamp():
            continue
        uuid = os.path.basename(path)[:-6]
        if me and uuid == me:
            continue
        sid = uuid[:8]
        title, turns, iv, prompts = read_session(path, clock)
        if not prompts:
            continue
        subs, sub_spans = subagents(path[:-6], clock)
        work = trim_wakes(union(iv + sub_spans), prompts)
        idle = [[work[i][1], work[i + 1][0]] for i in range(len(work) - 1) if work[i + 1][0] - work[i][1] >= 1]
        proj = os.path.basename(os.path.dirname(path))
        text = digest(sid, title, proj, path, turns, subs, clock)
        open(os.path.join(out, "digests", sid + ".md"), "w").write(text)
        day_turns = [u for u in turns if clock.inside(u["at"])]
        probe = " ".join([title or ""] + [u["prompt"][:400] for u in day_turns[:3]])
        hint = (pattern.findall(probe) or mr_pattern.findall(probe) or [None])[0]
        rows.append(dict(
            sid=sid, uuid=uuid, title=title or "", proj=proj, path=path, hint=hint,
            first_prompt=day_turns[0]["prompt"][:200] if day_turns else "",
            prompts=prompts, n_prompts=len(prompts),
            work=[[round(a, 1), round(b, 1)] for a, b in work], idle=[[round(a, 1), round(b, 1)] for a, b in idle],
            start=min(prompts), end=round(max(b for _, b in work), 1) if work else max(prompts),
            work_min=round(sum(b - a for a, b in work)), idle_min=round(sum(b - a for a, b in idle)),
            subagents=len(subs), tool_calls=sum(sum(u["tools"].values()) for u in day_turns), tool_errors=sum(u["errs"] for u in day_turns),
            digest_bytes=len(text),
        ))
    rows.sort(key=lambda r: r["start"])
    return rows


def run(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    return (p.stdout, None) if p.returncode == 0 else (None, (p.stderr or p.stdout)[-400:])


def iso(when):
    return when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect_jj(profile, clock, errors):
    lo, hi = iso(clock.lo), iso(clock.hi)
    rev = f'((author_date(after:"{lo}") & author_date(before:"{hi}")) | (committer_date(after:"{lo}") & committer_date(before:"{hi}"))) & mine()'
    tpl = 'change_id.short(8) ++ "\\t" ++ committer.timestamp().utc().format("%Y-%m-%dT%H:%M:%SZ") ++ "\\t" ++ bookmarks.join(",") ++ "\\t" ++ description.first_line() ++ "\\n"'
    commits = []
    for repo in profile.get("jj_repos", []):
        repo = os.path.expanduser(repo)
        text, err = run(["jj", "-R", repo, "log", "--ignore-working-copy", "--no-graph", "-r", rev, "-T", tpl])
        if err:
            errors.append(f"jj log {repo}: {err}")
            continue
        for line in text.splitlines():
            change, at, marks, desc = (line.split("\t") + ["", "", "", ""])[:4]
            if desc.strip():
                commits.append(dict(repo=os.path.basename(repo), change=change, t=round(clock.minute(parse_ts(at)), 1), bookmarks=marks, title=desc))
    ops = collections.Counter()
    repo = os.path.expanduser(profile.get("oplog_repo", ""))
    if repo:
        tpl = 'time.start().utc().format("%Y-%m-%dT%H:%M:%SZ") ++ "\\t" ++ description.first_line() ++ "\\n"'
        text, err = run(["jj", "-R", repo, "op", "log", "--ignore-working-copy", "--no-graph", "-n", "5000", "-T", tpl])
        if err:
            errors.append(f"jj op log: {err}")
        for line in (text or "").splitlines():
            at = parse_ts(line.split("\t")[0])
            if clock.inside(at):
                ops[int(clock.minute(at) // 10)] += 1
    return sorted(commits, key=lambda c: c["t"]), sorted(ops.items())


def glab_json(path, errors):
    text, err = run(["glab", "api", path, "--paginate"])
    if err:
        errors.append(f"glab {path.split('?')[0]}: {err}")
        return []
    out, dec, i = [], json.JSONDecoder(), 0
    while i < len(text):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            break
        obj, i = dec.raw_decode(text, i)
        out += obj if isinstance(obj, list) else [obj]
    return out


def collect_gitlab(profile, clock, errors):
    gl = profile.get("gitlab") or {}
    if not gl:
        return [], []
    after = (clock.lo.date() - dt.timedelta(days=1)).isoformat()
    before = (clock.hi.date() + dt.timedelta(days=1)).isoformat()
    events = []
    for e in sorted(glab_json(f"events?after={after}&before={before}&per_page=100", errors), key=lambda e: e["created_at"]):
        when = parse_ts(e["created_at"])
        if not clock.inside(when):
            continue
        t = round(clock.minute(when), 1)
        if e.get("target_type") == "MergeRequest":
            events.append(dict(t=t, a=e["action_name"], iid=e.get("target_iid"), title=(e.get("target_title") or "")[:90]))
        elif e.get("action_name", "").startswith("pushed"):
            events.append(dict(t=t, a="pushed", iid=None, title=(e.get("push_data") or {}).get("ref") or ""))
        elif e.get("note"):
            events.append(dict(t=t, a="commented", iid=(e.get("note") or {}).get("noteable_iid"), title=(e.get("target_title") or "")[:90]))
    mrs = []
    path = f"projects/{gl['project_id']}/merge_requests?author_username={gl['user']}&state=opened&per_page=100"
    for m in glab_json(path, errors):
        mrs.append(dict(iid=m["iid"], title=m["title"], draft=m.get("draft"), source=m["source_branch"], target=m["target_branch"],
                        status=m.get("detailed_merge_status"), conflicts=m.get("has_conflicts"), created=m["created_at"], updated=m["updated_at"], url=m.get("web_url")))
    return events, mrs


def make_groups(rows):
    big, short = collections.OrderedDict(), []
    for r in rows:
        if r["digest_bytes"] >= BIG_DIGEST:
            big.setdefault(r["hint"] or r["sid"], []).append(r)
        else:
            short.append(r)
    groups = [dict(name=k, kind="big", sids=[r["sid"] for r in v], size=sum(r["digest_bytes"] for r in v)) for k, v in big.items()]
    short_slots = max(1, -(-len(short) // SHORT_CHUNK)) if short else 0
    while len(groups) + short_slots > MAX_AGENTS and len(groups) > 1:
        groups.sort(key=lambda g: g["size"])
        a, b = groups.pop(0), groups.pop(0)
        groups.append(dict(name=f"{a['name']}+{b['name']}", kind="big", sids=a["sids"] + b["sids"], size=a["size"] + b["size"]))
    for i in range(short_slots):
        part = short[i * SHORT_CHUNK:(i + 1) * SHORT_CHUNK]
        groups.append(dict(name=f"short-runs-{i + 1}", kind="short", sids=[r["sid"] for r in part], size=sum(r["digest_bytes"] for r in part)))
    for g in groups:
        g["file"] = re.sub(r"[^A-Za-z0-9_.-]+", "-", g["name"]).strip("-") or g["sids"][0]
    return groups


def keep_groups(out, rows):
    old = read_json(os.path.join(out, "groups.json"))
    files = glob.glob(os.path.join(out, "analysis", "*.json"))
    if not old or not files:
        return None
    done = set()
    for f in files:
        try:
            done |= {x.get("sid", "")[:8] for x in json.load(open(f)).get("sessions", [])}
        except ValueError:
            pass
    known = {sid for g in old for sid in g["sids"]}
    new = [r["sid"] for r in rows if r["sid"] not in done and r["sid"] not in known]
    old = [g for g in old if g["file"] != "missing"]
    if new:
        old.append(dict(name="missing", kind="short", sids=new, size=0, file="missing"))
    return old


def render(template, **values):
    text = open(os.path.join(SKILL_DIR, "prompts", template)).read()
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def previous_tasks(out):
    root = os.path.dirname(out)
    days = sorted(d for d in os.listdir(root) if d < os.path.basename(out) and os.path.exists(os.path.join(root, d, "tasks.json")))
    return os.path.join(root, days[-1], "tasks.json") if days else "none"


def write_prompts(profile, day, clock, out, rows, groups):
    os.makedirs(os.path.join(out, "prompts"), exist_ok=True)
    os.makedirs(os.path.join(out, "analysis"), exist_ok=True)
    by_sid = {r["sid"]: r for r in rows}
    common = dict(DATE=day.isoformat(), TZ=profile.get("tz_label", profile["tz"].key), DAY_DIR=out,
                  THEMES=" | ".join(THEMES), KINDS=" | ".join(KINDS))
    for g in groups:
        lines = []
        for sid in g["sids"]:
            r = by_sid[sid]
            card = "short run: table row only" if g["kind"] == "short" else "big: gets a task card"
            lines.append(f"- {sid} · task hint: {r['hint'] or 'none'} · {card} · title: {r['title'][:80]} · first prompt: {r['first_prompt'][:120]!r}")
        text = render("analyst.md", SESSIONS="\n".join(lines), OUT_FILE=os.path.join(out, "analysis", g["file"] + ".json"), **common)
        open(os.path.join(out, "prompts", g["file"] + ".md"), "w").write(text)
    fix_paths = ", ".join(profile.get("fix_paths", []))
    text = render("wrap.md", PREV_TASKS=previous_tasks(out), FIX_PATHS=fix_paths, NOW=dt.datetime.now(profile["tz"]).strftime("%H:%M"), **common)
    open(os.path.join(out, "prompts", "wrap.md"), "w").write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("day", nargs="?", default="today")
    args = ap.parse_args()
    profile = load_profile()
    day = resolve_day(args.day, profile["tz"])
    clock = Clock(day, profile["tz"])
    out = day_dir(profile, day)
    os.makedirs(out, exist_ok=True)
    errors = []
    rows = collect_sessions(profile, clock, out)
    commits, ops = collect_jj(profile, clock, errors)
    events, mrs = collect_gitlab(profile, clock, errors)
    groups = keep_groups(out, rows) or make_groups(rows)
    write_json(os.path.join(out, "sessions_raw.json"), rows)
    write_json(os.path.join(out, "jj.json"), dict(commits=commits, ops=ops))
    write_json(os.path.join(out, "gitlab.json"), dict(events=events, open_mrs=mrs))
    write_json(os.path.join(out, "groups.json"), groups)
    write_json(os.path.join(out, "collect_errors.json"), errors)
    write_prompts(profile, day, clock, out, rows, groups)
    print(f"day {day} ({profile['tz'].key}) -> {out}")
    print(f"{len(rows)} sessions, {sum(r['n_prompts'] for r in rows)} prompts, {len(commits)} commits, {sum(n for _, n in ops)} jj ops, {len(events)} GitLab events, {len(mrs)} open MRs")
    for r in rows:
        print(f"  {r['sid']} {r['hint'] or '-':>8} work {r['work_min']:>4} stop {r['idle_min']:>4} prompts {r['n_prompts']:>3} digest {r['digest_bytes']:>6} | {r['title'][:60]}")
    print("agent groups:")
    for g in groups:
        print(f"  {g['file']}: {', '.join(g['sids'])} -> prompts/{g['file']}.md")
    print(f"linear: list_issues assignee=me updatedAt={iso(clock.lo)} -> write {out}/linear.json")
    for e in errors:
        print("ERROR", e)


if __name__ == "__main__":
    main()
