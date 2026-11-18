import argparse
import collections
import datetime as dt
import glob
import html
import json
import math
import os
import re

from common import BIG_DIGEST, KINDS, PHASES, SKILL_DIR, THEMES, Clock, day_dir, dur, hm, load_profile, parse_ts, read_json, resolve_day, write_json

STATES = ("ok", "warn", "crit")


def load_analysis(out, warnings):
    by_sid = {}
    for path in sorted(glob.glob(os.path.join(out, "analysis", "*.json"))):
        try:
            data = json.load(open(path))
        except ValueError as e:
            warnings.append(f"{os.path.basename(path)}: not valid JSON ({e})")
            continue
        for s in data.get("sessions", []):
            if s.get("sid"):
                by_sid[s["sid"][:8]] = s
    return by_sid


def short_label(text, size=20):
    return text if len(text) <= size else text[:size - 1].rstrip() + "…"


def clean_session(raw, a, short, warnings):
    sid = raw["sid"]
    if not a:
        warnings.append(f"{sid}: no analysis")
        a = {}
    for key in ("task", "label", "result", "phases", "bottlenecks"):
        if key not in a and a:
            warnings.append(f"{sid}: analysis has no '{key}'")
    task = (a.get("task") or raw.get("hint") or "Other")[:14]
    result = a.get("result") or {}
    state = result.get("state") if result.get("state") in STATES else "warn"
    phases = []
    for p in a.get("phases") or []:
        kind = p.get("kind") if p.get("kind") in PHASES else "admin"
        if p.get("kind") not in PHASES:
            warnings.append(f"{sid}: phase kind '{p.get('kind')}' is not known")
        phases.append(dict(kind=kind, minutes=max(0, round(float(p.get("minutes") or 0))), what=p.get("what", "")))
    return dict(
        sid=sid, task=task, label=short_label(a.get("label") or raw["title"] or sid), name=a.get("name") or "",
        short=short, result=dict(state=state, text=result.get("text") or (a.get("outcome") or "")[:40]),
        phases=phases, facts=a.get("facts") or [], outcome=a.get("outcome", ""),
        prompts=raw["prompts"], work=raw["work"], idle=raw["idle"], start=raw["start"], end=raw["end"],
        work_min=raw["work_min"], idle_min=raw["idle_min"], n_prompts=raw["n_prompts"], subagents=raw["subagents"],
    )


def findings(sessions, analysis, warnings):
    out = []
    for s in sessions:
        for n, b in enumerate((analysis.get(s["sid"]) or {}).get("bottlenecks") or [], 1):
            minutes = float(b.get("minutes") or 0)
            if minutes < 1:
                continue
            theme = b.get("theme") if b.get("theme") in THEMES else "Other"
            kind = b.get("kind") if b.get("kind") in KINDS else "other"
            if b.get("theme") not in THEMES:
                warnings.append(f"{s['sid']}: theme '{b.get('theme')}' is not known")
            what = b.get("what_happened", "")
            out.append(dict(id=b.get("id") or f"{s['sid']}-{n}", sid=s["sid"], task=s["task"], label=s["label"], kind=kind, theme=theme,
                            start=b.get("start", ""), min=round(minutes, 1), short=b.get("short") or what.split(". ")[0][:80], what=what, fix=b.get("avoidable_how", "")))
    return out


def linear_rows(out, clock, warnings):
    data = read_json(os.path.join(out, "linear.json"))
    if data is None:
        warnings.append("linear.json is missing")
        return []
    items = data if isinstance(data, list) else data.get("issues") or data.get("nodes") or data.get("data") or []
    rows = []
    for it in items:
        status = it.get("status") or it.get("state") or ""
        status = status.get("name", "") if isinstance(status, dict) else status

        def at(key):
            v = it.get(key)
            if not v:
                return None
            when = parse_ts(v)
            return round(clock.minute(when), 1) if clock.inside(when) else None
        rows.append(dict(id=it.get("identifier") or it.get("id"), title=it.get("title", ""), status=status,
                         created=at("createdAt"), started=at("startedAt"), completed=at("completedAt"), canceled=at("canceledAt")))
    return rows


def stacks(mrs, pattern):
    by_source = {m["source"]: m for m in mrs}
    children = collections.defaultdict(list)
    for m in mrs:
        if m["target"] in by_source:
            children[m["target"]].append(m)
    chains = []
    for m in sorted(mrs, key=lambda m: m["iid"]):
        if m["target"] in by_source or not children.get(m["source"]):
            continue
        chain, cur = [m], m
        while children.get(cur["source"]):
            cur = sorted(children[cur["source"]], key=lambda c: c["iid"])[0]
            chain.append(cur)
        chains.append(dict(base=m["target"], mrs=[dict(iid=c["iid"], title=c["title"], draft=c["draft"], conflicts=c["conflicts"],
                                                       ticket=(pattern.findall(c["title"] + " " + c["source"]) or [""])[0]) for c in chain]))
    return chains


def away_gaps(sessions):
    all_p = sorted(p for s in sessions for p in s["prompts"])
    return [(a, b) for a, b in zip(all_p, all_p[1:]) if b - a >= 20]


def peak(sessions):
    edges = sorted([(a, 1) for s in sessions for a, _ in s["work"]] + [(b, -1) for s in sessions for _, b in s["work"]])
    best, at, n = 0, 0, 0
    for t, d in edges:
        n += d
        if n > best:
            best, at = n, t
    return best, at


def kpis(sessions, events, linear, commits, ops):
    first = min(s["start"] for s in sessions)
    last = max(s["end"] for s in sessions)
    work = sum(s["work_min"] for s in sessions)
    idle = sum(s["idle_min"] for s in sessions)
    gaps = away_gaps(sessions)
    merged = sorted({e["iid"] for e in events if e["a"] == "accepted" and e["iid"]})
    opened = sorted({e["iid"] for e in events if e["a"] == "opened" and e["iid"]})
    approved = sorted({e["iid"] for e in events if e["a"] == "approved" and e["iid"]})
    created = [t for t in linear if t["created"] is not None]
    started = [t for t in linear if t["started"] is not None]
    done = [t for t in linear if t["completed"] is not None]
    n_peak, at_peak = peak(sessions)
    share = round(idle / (work + idle) * 100) if work + idle else 0
    ids = lambda xs: " · ".join(f"!{i}" for i in xs[:4]) + (" …" if len(xs) > 4 else "")
    return [
        [dur(last - first), f"first prompt {hm(first)}, last activity {hm(last)}"],
        [f"{len(sessions)} sessions", f"{sum(s['n_prompts'] for s in sessions)} prompts · {sum(s['subagents'] for s in sessions)} subagents"],
        [f"{dur(work)} work", f"{dur(idle)} stopped · {share}% of session time"],
        [dur(sum(b - a for a, b in gaps)), f"with no prompt in any session, in {len(gaps)} gaps"],
        [f"{len(merged)} merged", ids(merged) or "no MR merged"],
        [f"{len(opened)} MRs opened", (ids(opened) or "none") + (f" · {len(approved)} approved" if approved else "")],
        [f"{len(created)} tickets", f"created · {len(started)} started · {len(done)} done"],
        [f"{len(commits)} commits", f"{sum(n for _, n in ops)} jj operations · {n_peak} sessions at once at {hm(at_peak)}"],
    ], merged, opened


def build_report(profile, day, out, warnings):
    clock = Clock(day, profile["tz"])
    raw = read_json(os.path.join(out, "sessions_raw.json"), [])
    analysis = load_analysis(out, warnings)
    sessions = [clean_session(r, analysis.get(r["sid"]), r["digest_bytes"] < BIG_DIGEST, warnings) for r in raw]
    if not sessions:
        raise SystemExit("No sessions on this day.")
    pattern = re.compile(profile.get("ticket_pattern", r"\b[A-Z]{2,5}-\d+\b"))
    keep = {s["task"] for s in sessions if not s["short"] or pattern.search(s["task"])} | {"Tooling"}
    for s in sessions:
        if s["task"] not in keep:
            s["task"] = "Side runs"
    order = []
    for s in sorted(sessions, key=lambda s: s["start"]):
        if s["task"] not in order:
            order.append(s["task"])
    order.sort(key=lambda t: (t == "Tooling", t == "Side runs"))
    jj = read_json(os.path.join(out, "jj.json"), dict(commits=[], ops=[]))
    gl = read_json(os.path.join(out, "gitlab.json"), dict(events=[], open_mrs=[]))
    linear = linear_rows(out, clock, warnings)
    tasks = read_json(os.path.join(out, "tasks.json"))
    opened = read_json(os.path.join(out, "open.json"))
    if tasks is None:
        warnings.append("tasks.json is missing")
    if opened is None:
        warnings.append("open.json is missing")
    kpi, merged, mr_opened = kpis(sessions, gl["events"], linear, jj["commits"], jj["ops"])
    now = dt.datetime.now(profile["tz"])
    data_to = now.strftime("%H:%M") if now < clock.hi else None
    tz_label = profile.get("tz_label", profile["tz"].key)
    sub = f"all times {tz_label} · {len(sessions)} sessions · {sum(s['n_prompts'] for s in sessions)} prompts · {len(merged)} MRs merged · {len(mr_opened)} opened" + (f" · data to {data_to}" if data_to else "")
    t0 = math.floor(min(s["start"] for s in sessions) / 60) * 60
    t1 = max(t0 + 60, math.ceil(max(s["end"] for s in sessions) / 60) * 60)
    return dict(
        meta=dict(date=day.isoformat(), title=f"Day report · {day.day} {day.strftime('%b %Y')}",
                  h1=f"Day report · {day.strftime('%A')} {day.day} {day.strftime('%B %Y')}", sub=sub, tz=profile["tz"].key, tz_label=tz_label, data_to=data_to),
        axis=dict(t0=t0, t1=t1), tasks_order=order, kpis=kpi, sessions=sessions, finds=findings(sessions, analysis, warnings),
        gitlab=gl["events"], linear=linear, ops=jj["ops"], commits=jj["commits"], stacks=stacks(gl["open_mrs"], pattern),
        open=[o for o in (opened or []) if isinstance(o, dict)], tasks=[t for t in (tasks or []) if isinstance(t, dict)],
    )


def assemble(report, out):
    base_path = os.path.join(os.path.dirname(SKILL_DIR), "daniel-artifact", "base.html")
    base = open(base_path).read()
    head, rest = base.split("/* page */\n</style>")
    script = rest[rest.index("<script>") + 8: rest.rindex("</script>")]
    chips = report["tasks_order"] + THEMES
    script = script.replace("const CHIP_ORDER = [];", "const CHIP_ORDER = " + json.dumps(chips) + ";")
    head = head.replace("<title>PAGE TITLE</title>", f"<meta charset=\"utf-8\">\n<title>{html.escape(report['meta']['title'])}</title>")
    tpl = lambda name: open(os.path.join(SKILL_DIR, "template", name)).read()
    body = tpl("body.html").replace("{{H1}}", html.escape(report["meta"]["h1"])).replace("{{SUB}}", html.escape(report["meta"]["sub"]))
    data = ("const REPORT = " + json.dumps(report, ensure_ascii=False) + ";\n").replace("</", "<\\/")
    page = head + "/* page */\n" + tpl("page.css") + "</style>\n\n" + body + "\n<script>\n" + script + "\n" + data + tpl("page.js") + "</script>\n"
    os.makedirs(os.path.join(out, "page"), exist_ok=True)
    path = os.path.join(out, "page", "index.html")
    open(path, "w").write(page)
    return path, len(page)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("day", nargs="?", default="today")
    args = ap.parse_args()
    profile = load_profile()
    day = resolve_day(args.day, profile["tz"])
    out = day_dir(profile, day)
    warnings = []
    report = build_report(profile, day, out, warnings)
    write_json(os.path.join(out, "report.json"), report)
    path, size = assemble(report, out)
    write_json(os.path.join(out, "build_warnings.json"), warnings)
    print(f"{path} ({size // 1024} KB)")
    print(f"title: {report['meta']['title']}")
    print(f"{len(report['sessions'])} sessions, {len(report['finds'])} findings, {len(report['tasks'])} tasks, {len(report['open'])} open items, {len(report['stacks'])} MR stacks")
    for k in report["kpis"]:
        print("  kpi:", " | ".join(k))
    for w in warnings:
        print("WARN", w)


if __name__ == "__main__":
    main()
