#!/usr/bin/env python3
"""Ask before jj git push moves a bookmark that no glob in push-allow matches."""
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

PUSH = re.compile(r"\bjj\s+(?:[^\s|;&]+\s+)*?git\s+push\b[^;&|]*")
MOVED = re.compile(r"^\s*bookmark: (\S+) \[", re.M)
ALLOW = Path(os.environ.get("SKILLS_AGENTS_PRIVATE", Path.home() / ".config/skills-agents")) / "push-allow"


def dry_run(segment, cwd):
    try:
        args = shlex.split(segment)
    except ValueError:
        return None
    if any("$" in arg for arg in args):
        return None
    try:
        result = subprocess.run(args + ["--dry-run"], cwd=cwd or None,
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout + result.stderr if result.returncode == 0 else None


def reason(command, cwd, allowed, run=dry_run):
    match = PUSH.search(command)
    if not match or not allowed:
        return None
    output = run(match.group(0).strip(), cwd)
    if output is None:
        return "Could not dry-run this push to list the bookmarks it moves."
    foreign = [name for name in MOVED.findall(output)
               if not any(fnmatch.fnmatchcase(name, glob) for glob in allowed)]
    if not foreign:
        return None
    return "This push moves bookmarks outside push-allow: " + ", ".join(foreign)


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    allowed = ALLOW.read_text().split() if ALLOW.is_file() else []
    text = reason((event.get("tool_input") or {}).get("command", ""), event.get("cwd"), allowed)
    if text:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": text,
        }}))
    return 0


def test():
    out = ("Changes to push to origin:\n"
           "  bookmark: danielsorichetti/x [move forward from a to b]\n"
           "  bookmark: user/prowe/y [move forward from a to b]\n")
    mine = ["danielsorichetti/*"]
    assert reason("jj log", "", mine, lambda s, c: out) is None
    assert reason("jj git push", "", [], lambda s, c: out) is None
    assert reason("jj git push --tracked", "", mine, lambda s, c: out).endswith("user/prowe/y")
    assert reason("jj git push -b danielsorichetti/x", "", mine,
                  lambda s, c: out.splitlines()[1]) is None
    assert reason("jj git push", "", mine, lambda s, c: None).startswith("Could not")
    seen = []
    reason("cd x && jj -R r git push -b a && echo done", "", mine, lambda s, c: seen.append(s) or "")
    assert seen == ["jj -R r git push -b a"], seen
    assert dry_run('jj -R "$REPO" git push', "") is None
    print("ok")


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv else main())
