#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

TRUNK = "main@origin"
SEP = "\x1f"
COMMIT_T = (
    'change_id.short(8) ++ "\x1f" ++ commit_id ++ "\x1f" ++ '
    'local_bookmarks.map(|b| b.name()).join(",") ++ "\x1f" ++ '
    'if(conflict, "C", "") ++ "\x1f" ++ description.first_line() ++ "\n"'
)
BOOKMARK_T = (
    'name ++ "\x1f" ++ if(remote, remote, "") ++ "\x1f" ++ '
    'if(normal_target, normal_target.commit_id(), "") ++ "\n"'
)


def run(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd[:3])}: {r.stderr.strip()[:300]}")
    return r.stdout


def commits(revset):
    rows = []
    for line in run("jj", "log", "--no-graph", "-r", revset, "-T", COMMIT_T).splitlines():
        change, commit, marks, conflict, title = line.split(SEP)
        rows.append(dict(change=change, commit=commit, bookmarks=[b for b in marks.split(",") if b], conflict=bool(conflict), title=title))
    return rows


def api(path):
    return json.loads(run("glab", "api", path))


def window_start(days):
    d = dt.date.today()
    while days:
        d -= dt.timedelta(days=1)
        days -= d.weekday() < 5
    return d


def remote_heads():
    heads = {}
    for line in run("jj", "bookmark", "list", "-a", "-T", BOOKMARK_T).splitlines():
        name, remote, commit = line.split(SEP)
        if remote == "origin":
            heads[name] = commit
    return heads


def latest_mr(branch):
    rows = api(f"projects/:id/merge_requests?source_branch={quote(branch, safe='')}&state=all&order_by=updated_at&per_page=1")
    return rows[0] if rows else None


def open_threads(iid):
    found = api(f"projects/:id/merge_requests/{iid}/discussions?per_page=100")
    return sum(1 for d in found if d["notes"][0].get("resolvable") and not d["notes"][0].get("resolved"))


def merged_commits(sha):
    try:
        return {c["change"]: c["commit"] for c in commits(f"::{sha} ~ ::{TRUNK}")}
    except RuntimeError:
        return None


def changed_lines(*args):
    lines, path = set(), None
    for line in run("jj", "diff", "--git", *args).splitlines():
        if line.startswith("diff --git"):
            path = line
        elif line[:1] in "+-" and not line.startswith(("+++", "---")):
            lines.add((path, line))
    return lines


def squash_matches(tip, mr):
    squash = mr.get("squash_commit_sha") or mr.get("merge_commit_sha")
    if not squash:
        return False
    try:
        return changed_lines("--from", f"fork_point({tip} | {TRUNK})", "--to", tip) == changed_lines("-r", squash)
    except RuntimeError:
        return False


def classify(branch, own, tip, mr, pushed_at):
    if not mr:
        return ("NO-MR" if pushed_at else "UNPUSHED"), "", set()
    head = f"!{mr['iid']} {mr['state']}"
    if mr["state"] == "merged":
        if mr["target_branch"] != "main":
            return "CHECK", f"{head} into {mr['target_branch']}, not main", set()
        merged = merged_commits(mr["sha"])
        if merged is None or any(c["change"] not in merged or merged[c["change"]] != c["commit"] for c in own):
            if squash_matches(tip, mr):
                return "MERGED", f"{head}, same diff as its squash on main", {c["change"] for c in own}
        if merged is None:
            return "CHECK", f"{head}: MR head {mr['sha'][:12]} is not in the repo", set()
        same = {c["change"] for c in own if merged.get(c["change"]) == c["commit"]}
        rewritten = [c["change"] for c in own if c["change"] in merged and c["change"] not in same]
        after = [c["change"] for c in own if c["change"] not in merged]
        if rewritten:
            return "CHECK", f"{head}, {len(rewritten)} commit(s) rewritten after the merge: jj interdiff --from {mr['sha'][:12]} --to {branch}", same
        if after:
            return "AFTER-MERGE", f"{head}, {len(after)} commit(s) after the merge need a new MR", same
        return "MERGED", head, same
    if mr["state"] != "opened":
        return "CLOSED", head, set()
    mr = api(f"projects/:id/merge_requests/{mr['iid']}")
    pipe = (mr.get("head_pipeline") or {}).get("status")
    local = "" if mr["sha"] == tip else " local-differs-from-MR"
    draft = " draft" if mr.get("draft") else ""
    return "OPEN", f"{head}{draft} {mr['detailed_merge_status']} pipeline={pipe} threads={open_threads(mr['iid'])}{local}", set()


def print_subjects(rows, limit=6):
    for c in rows[:limit]:
        print(f"{'':14}- {c['title']}")
    if len(rows) > limit:
        print(f"{'':14}- and {len(rows) - limit} more")


def main():
    p = argparse.ArgumentParser(description="Sort recent jj work into done, pending and needs attention, with the jj commands to clean it.")
    p.add_argument("--days", type=int, default=2, help="working days back, today excluded (default 2)")
    p.add_argument("--since", help="YYYY-MM-DD, overrides --days")
    a = p.parse_args()
    start = a.since or window_start(a.days).isoformat()
    me = api("user")["username"]
    print(f"WINDOW since {start} (machine time), user {me}")

    recent = f'mine() & mutable() & ~::{TRUNK} & ~empty() & (author_date(after:"{start}") | committer_date(after:"{start}"))'
    scope_rs = f"(::(({recent})::) ~ ::{TRUNK}) ~ (empty() & description(exact:\"\"))"
    scope = commits(scope_rs)
    names = sorted({b for c in scope for b in c["bookmarks"]})
    handoffs = [b for b in names if b.startswith("handoff/")]
    branches = [b for b in names if b not in handoffs]
    pushed = remote_heads()

    with ThreadPoolExecutor(8) as pool:
        ancestry = dict(zip(branches, pool.map(lambda b: commits(f"::{b} ~ ::{TRUNK}"), branches)))
        mrs = dict(zip(branches, pool.map(latest_mr, branches)))

    sets = {b: {c["change"] for c in rows} for b, rows in ancestry.items()}
    own = {b: [c for c in ancestry[b] if not any(c["change"] in sets[o] for o in branches if o != b and sets[o] < sets[b])] for b in branches}
    tips = {b: ancestry[b][0]["commit"] for b in branches}

    abandon, forget, seen_mrs, held = set(), [], set(), set()
    print("\nBRANCHES (verdict, branch, commits, MR, notes)")
    with ThreadPoolExecutor(8) as pool:
        results = dict(zip(branches, pool.map(lambda b: classify(b, own[b], tips[b], mrs[b], pushed.get(b)), branches)))
    for b in branches:
        verdict, note, merged = results[b]
        if mrs[b]:
            seen_mrs.add(mrs[b]["iid"])
        abandon |= merged
        if verdict == "MERGED":
            forget.append(b)
        if verdict == "CHECK":
            held |= {c["change"] for c in own[b]}
        sync = "" if pushed.get(b) in (None, tips[b]) else " unpushed-rewrite"
        conflicts = sum(c["conflict"] for c in own[b])
        flag = f" conflicts={conflicts}" if conflicts else ""
        title = mrs[b]["title"] if mrs[b] else ancestry[b][0]["title"]
        print(f"{verdict:12} {b}  n={len(own[b])}{flag}{sync}  {note}  | {title}")
        print_subjects([c for c in own[b] if c["title"] != title])

    loose = [c for c in scope if not any(c["change"] in sets[b] for b in branches)]
    for c in loose:
        print(f"{'NO-BOOKMARK':12} {c['change']}  | {c['title']}")
    for h in handoffs:
        print(f"{'HANDOFF':12} {h}  parked work: /daniel-integrate lands it, or delete it if its branch already has it")
        print_subjects(commits(f"::{h} ~ ::{TRUNK}"))

    since = f"{start}T00:00:00Z"
    done = [m for m in api(f"projects/:id/merge_requests?author_username={me}&state=merged&updated_after={since}&per_page=100") if (m.get("merged_at") or "") >= since]
    print("\nMERGED SINCE WINDOW START (author me)")
    for m in sorted(done, key=lambda m: m["merged_at"]):
        print(f"  !{m['iid']} {m['merged_at'][:16]}  {m['title']}")
    elsewhere = [m for m in api(f"projects/:id/merge_requests?author_username={me}&state=opened&per_page=100") if m["iid"] not in seen_mrs]
    print("\nOPEN MRS OUTSIDE THE WINDOW")
    for m in elsewhere:
        print(f"  !{m['iid']} {m['detailed_merge_status']}  {m['source_branch']}  | {m['title']}")

    if held:
        held = {c["change"] for c in commits(f"({'|'.join(held)})::")}
    remaining = [c["change"] for c in scope if c["change"] not in abandon | held]
    old = commits(f"conflicts() & mine() & mutable() ~ ({scope_rs})")
    print("\nCOMMANDS")
    if abandon:
        print("ABANDON  jj abandon " + " ".join(sorted(abandon)))
    if forget:
        print("FORGET   jj bookmark forget " + " ".join(forget))
    if remaining:
        print(f"REBASE   jj rebase -s 'roots({'|'.join(remaining)}) ~ children({TRUNK})' -d {TRUNK} --skip-emptied")
    if held:
        print("HELD     not rebased, CHECK stacks and their descendants: " + " ".join(sorted(held & {c['change'] for c in scope})))
    print(f"\nOLD CONFLICTS outside the window: {len(old)} commit(s), left alone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
