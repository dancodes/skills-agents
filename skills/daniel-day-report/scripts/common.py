import datetime as dt
import json
import os
import sys
from zoneinfo import ZoneInfo

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES = ["Approval stops", "Review and decision loops", "Proof videos", "Tests, CI, rebase", "Spec changed mid-run", "Other"]
KINDS = ["user-wait", "agent-slow", "rework", "scope-creep", "waiting-on-ci-or-review", "tool-failure", "unclear-prompt", "other"]
BIG_DIGEST = 7000
PHASES = ["plan", "build", "proof", "wait", "ci", "rework", "admin"]


def load_profile():
    root = os.environ.get("SKILLS_AGENTS_PRIVATE") or os.path.expanduser("~/.config/skills-agents")
    path = os.path.join(root, "day-report.json")
    if not os.path.exists(path):
        sys.exit(f"No profile at {path}. Ask Daniel for one.")
    profile = json.load(open(path))
    profile["tz"] = ZoneInfo(profile.get("timezone", "UTC"))
    return profile


def resolve_day(arg, tz):
    today = dt.datetime.now(tz).date()
    if arg in (None, "", "today"):
        return today
    if arg == "yesterday":
        return today - dt.timedelta(days=1)
    return dt.date.fromisoformat(arg)


def day_bounds(day, tz):
    lo = dt.datetime.combine(day, dt.time(0), tz)
    hi = dt.datetime.combine(day + dt.timedelta(days=1), dt.time(0), tz)
    return lo, hi


def day_dir(profile, day):
    return os.path.join(os.path.expanduser(profile.get("out_dir", "~/dayreports")), day.isoformat())


def parse_ts(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


class Clock:
    def __init__(self, day, tz):
        self.tz = tz
        self.lo, self.hi = day_bounds(day, tz)

    def inside(self, when):
        return self.lo <= when < self.hi

    def minute(self, when):
        return (when - self.lo).total_seconds() / 60

    def hm(self, when):
        return when.astimezone(self.tz).strftime("%H:%M")


def hm(minutes):
    m = int(round(minutes))
    return f"{m // 60:02d}:{m % 60:02d}"


def dur(minutes):
    m = int(round(minutes))
    return f"{m} min" if m < 60 else f"{m // 60} h {m % 60:02d} min"


def write_json(path, data, indent=1):
    with open(path, "w") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)
