#!/usr/bin/env python3
import argparse
import json
import statistics
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TRANSIENT_MERGE_STATUS = {"checking", "unchecked", "preparing", "approvals_syncing"}
STUCK_FACTOR = 3
MIN_HISTORY = 3


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--tz", required=True)
    p.add_argument("--ignore", default="", help="comma-separated usernames whose notes are not reviews")
    p.add_argument("--state", required=True)
    p.add_argument("--interval", type=int, default=60)
    p.add_argument("--once", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("mrs", nargs="+", help="IID@HH:MM")
    return p.parse_args()


class Gitlab:
    def __init__(self, project, dry_run):
        self.project = project
        self.base = "projects/" + urllib.parse.quote(project, safe="")
        self.dry_run = dry_run

    def get(self, path):
        out = subprocess.run(["glab", "api", self.base + path], capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            raise RuntimeError(out.stderr.strip().splitlines()[-1] if out.stderr.strip() else "glab api failed")
        return json.loads(out.stdout)

    def act(self, *args):
        cmd = ["glab", "mr", *args, "-R", self.project]
        if self.dry_run:
            return "dry-run: " + " ".join(cmd)
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        lines = (out.stdout + out.stderr).strip().splitlines()
        return ("ok: " if out.returncode == 0 else "failed: ") + (lines[-1] if lines else "")


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def seen(self, key):
        return (self.root / key).exists()

    def mark(self, key, value=""):
        (self.root / key).write_text(value)

    def read(self, key):
        f = self.root / key
        return f.read_text() if f.exists() else None


def deadline_today(hhmm, tz):
    h, m = map(int, hhmm.split(":"))
    return datetime.now(tz).replace(hour=h, minute=m, second=0, microsecond=0)


def review_comments(gl, iid, me, ignore):
    notes = gl.get(f"/merge_requests/{iid}/notes?per_page=100")
    return sum(1 for n in notes if not n["system"] and n["author"]["username"] not in ignore | {me})


def open_threads(gl, iid):
    discussions = gl.get(f"/merge_requests/{iid}/discussions?per_page=100")
    return sum(1 for d in discussions for n in d["notes"][:1] if n.get("resolvable") and not n.get("resolved"))


def usual_duration(gl, store, name):
    key = "usual-" + name.replace("/", "_")
    cached = store.read(key)
    if cached is not None:
        return float(cached) if cached else None
    jobs = gl.get("/jobs?scope[]=success&per_page=100")
    durations = [j["duration"] for j in jobs if j["name"] == name and j.get("duration")]
    value = statistics.median(durations) if len(durations) >= MIN_HISTORY else None
    store.mark(key, "" if value is None else str(value))
    return value


def pipeline_jobs(gl, pipeline_id):
    return gl.get(f"/pipelines/{pipeline_id}/jobs?per_page=100")


def stuck_lines(gl, store, iid, jobs):
    lines = []
    now = datetime.now(ZoneInfo("UTC"))
    for j in jobs:
        if j["status"] != "running" or not j.get("started_at"):
            continue
        usual = usual_duration(gl, store, j["name"])
        if not usual:
            continue
        ran = (now - datetime.fromisoformat(j["started_at"].replace("Z", "+00:00"))).total_seconds()
        key = f"stuck-{j['id']}"
        if ran > STUCK_FACTOR * usual and not store.seen(key):
            store.mark(key)
            lines.append(f"!{iid} STUCK job {j['id']} {j['name']} running {ran / 60:.0f}m, usual {usual / 60:.0f}m {j['web_url']}")
    return lines


def snapshot(gl, store, iid, me, ignore):
    mr = gl.get(f"/merge_requests/{iid}")
    approvals = gl.get(f"/merge_requests/{iid}/approvals")
    hp = mr.get("head_pipeline") or {}
    status = mr.get("detailed_merge_status")
    last_status_key = f"{iid}.merge_status"
    if status in TRANSIENT_MERGE_STATUS:
        status = store.read(last_status_key) or status
    else:
        store.mark(last_status_key, status or "")
    jobs = pipeline_jobs(gl, hp["id"]) if hp.get("id") and hp.get("status") in ("running", "failed") else []
    failed = sorted(f"{j['name']}:{j['id']}" for j in jobs if j["status"] == "failed" and not j.get("allow_failure"))
    return {
        "state": mr["state"],
        "sha": mr["sha"][:10],
        "pipeline": f"{hp.get('id')}:{hp.get('status')}",
        "failed_jobs": ",".join(failed) or "-",
        "approved": bool(approvals.get("approved")) and bool(approvals.get("approved_by")),
        "automerge": bool(mr.get("merge_when_pipeline_succeeds")),
        "merge_status": status,
        "conflicts": bool(mr.get("has_conflicts")),
        "comments": review_comments(gl, iid, me, ignore),
        "open_threads": open_threads(gl, iid),
        "branch": mr["source_branch"],
        "_jobs": jobs,
    }


def act(gl, store, iid, snap, deadline, now):
    lines = []
    if snap["state"] != "opened":
        return lines
    past_deadline = now >= deadline
    approved = snap["approved"]
    if past_deadline and not approved:
        key = f"{iid}.approve-{snap['sha']}"
        if not store.seen(key):
            store.mark(key)
            lines.append(f"!{iid} deadline reached, approve: {gl.act('approve', str(iid))}")
        approved = True
    early = approved and snap["comments"] == 0
    if (past_deadline or early) and approved and not snap["automerge"]:
        key = f"{iid}.automerge-{snap['sha']}-{snap['merge_status']}"
        if not store.seen(key):
            store.mark(key)
            reason = "deadline reached" if past_deadline else "approved with no review comments"
            lines.append(f"!{iid} {reason}, auto-merge: {gl.act('merge', str(iid), '--auto-merge', '--yes')}")
    return lines


def status_line(iid, snap, deadline):
    fields = {k: v for k, v in snap.items() if not k.startswith("_")}
    body = " ".join(f"{k}={v}" for k, v in fields.items())
    return f"!{iid} deadline={deadline:%H:%M} {body}"


def tick(gl, store, targets, me, ignore, tz):
    out = []
    now = datetime.now(tz)
    for iid, deadline in list(targets.items()):
        try:
            snap = snapshot(gl, store, iid, me, ignore)
            out += act(gl, store, iid, snap, deadline, now)
            out += stuck_lines(gl, store, iid, snap["_jobs"])
        except Exception as e:
            key = f"{iid}.error"
            if store.read(key) != str(e):
                store.mark(key, str(e))
                out.append(f"!{iid} ERROR {e}")
            continue
        store.mark(f"{iid}.error", "")
        line = status_line(iid, snap, deadline)
        key = f"{iid}.last"
        if store.read(key) != line:
            store.mark(key, line)
            out.append(f"{now:%H:%M} {line}")
        if snap["state"] in ("merged", "closed"):
            del targets[iid]
    return out


def main():
    args = parse_args()
    tz = ZoneInfo(args.tz)
    gl = Gitlab(args.project, args.dry_run)
    store = Store(args.state)
    ignore = {u for u in args.ignore.split(",") if u}
    me = json.loads(subprocess.run(["glab", "api", "user"], capture_output=True, text=True, check=True).stdout)["username"]
    targets = {}
    for spec in args.mrs:
        iid, hhmm = spec.split("@")
        targets[int(iid)] = deadline_today(hhmm, tz)
    if store.read("cutoff") is None:
        store.mark("cutoff", (deadline_today("00:00", tz) + timedelta(days=1)).isoformat())
    cutoff = datetime.fromisoformat(store.read("cutoff"))
    while True:
        for line in tick(gl, store, targets, me, ignore, tz):
            print(line, flush=True)
        if not targets:
            print("ALL DONE", flush=True)
            return 0
        if args.once:
            return 0
        if datetime.now(tz) >= cutoff:
            print("CUTOFF midnight reached, still open: " + " ".join(f"!{i}" for i in targets), flush=True)
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
