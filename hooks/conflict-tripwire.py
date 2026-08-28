#!/usr/bin/env python3
"""Report every conflicted commit right after a jj command that can create one.

A misplaced squash cascades a conflict to every descendant, including the
working copies other agents are sitting on. Caught on the operation that caused
it the fix is one forward squash; caught later the cause is buried under other
people's operations, and jj undo has no target to aim at it.

Read-only, and --ignore-working-copy keeps a hook that fires on every Bash call
from snapshotting a working copy another agent is editing.
"""
import json
import re
import subprocess
import sys

# Commands that rewrite commit content, so they can leave a conflict behind.
REWRITES = re.compile(r"\bjj\s+(?:[^\s|;&]+\s+)*?(?:squash|rebase|split|absorb|restore|backout|revert|edit)\b")
LISTED = 10
TEMPLATE = ('change_id.shortest(8) ++ "\\t" ++ bookmarks.join(" ") ++ "\\t" '
            '++ description.first_line() ++ "\\n"')


def jj(args, cwd):
    try:
        result = subprocess.run(
            ["jj", "--ignore-working-copy", "--color=never", "log", "--no-graph"] + args,
            cwd=cwd or None, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def rows(revset, cwd, run):
    out = run(["-r", revset, "-T", TEMPLATE], cwd)
    if out is None:
        return []
    return [line.split("\t") for line in out.splitlines() if line.strip()]


def parked(bookmarks):
    names = [b.rstrip("*?") for b in bookmarks.split()]
    return bool(names) and all(n.startswith("handoff/") for n in names)


def warning(command, cwd, run=jj):
    if not REWRITES.search(command or ""):
        return None
    conflicted = rows("conflicts()", cwd, run)
    if not conflicted:
        return None
    live = {row[0] for row in rows("conflicts() & working_copies()", cwd, run)}

    lines = [f"{len(conflicted)} commit(s) are in a conflicted state after this command."]
    for cid, bookmarks, description in conflicted[:LISTED]:
        tags = [t for t in (bookmarks, "another workspace's working copy" if cid in live else "") if t]
        suffix = f"  [{', '.join(tags)}]" if tags else ""
        lines.append(f"  {cid}  {description or '(no description)'}{suffix}")
    if len(conflicted) > LISTED:
        lines.append(f"  ... and {len(conflicted) - LISTED} more")
    if live:
        lines.append(f"\n{len(live)} of these are working copies other agents are sitting on.")
    if all(parked(bookmarks) for _, bookmarks, _ in conflicted):
        lines.append(
            "\nAll of these are parked handoff bookmarks, conflicted because the\n"
            "rebase moved them onto the new base. Not yours to fix: keep executing\n"
            "the plan and name them in your report. The next integrator lands them."
        )
    else:
        lines.append(
            "\nStop. Run no further squashes from the plan. The usual cause is a file\n"
            "squashed into a commit that never touched it, so correct it forward by\n"
            "squashing that content into the commit that owns it, then re-check\n"
            "`jj log -r 'conflicts()'`. Never jj undo: it has no target and takes\n"
            "whichever operation landed last in this shared repository."
        )
    return "\n".join(lines)


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool_input = event.get("tool_input") or {}
    text = warning(tool_input.get("command", ""), event.get("cwd"))
    if not text:
        return 0
    print(text, file=sys.stderr)
    return 2


def test():
    assert REWRITES.search("jj squash --into abc a.ts")
    assert REWRITES.search("jj op revert 197d348a40f5")
    assert REWRITES.search("cd /repo && jj rebase -r abc -d xyz")
    # Returning from a conflict resolution is when it gets snapshotted and rebased.
    assert REWRITES.search("jj edit abc")
    assert not REWRITES.search("jj log -r 'conflicts()'")
    assert not REWRITES.search("jj describe -r abc -m 'x'")

    conflicted = ("xykttnxu\t\twrap up disaster mitigation\n"
                  "mxxluvkm\tfeature/tf-10511\tsection previews\n"
                  "yuptvnkq\t\t\n")

    def fake(args, cwd):
        return "yuptvnkq\t\t\n" if "working_copies" in args[1] else conflicted

    text = warning("jj squash --into xykttnxu a.ts", None, fake)
    assert "3 commit(s)" in text, text
    assert "feature/tf-10511" in text
    assert "another workspace's working copy" in text
    assert "(no description)" in text
    assert "1 of these are working copies" in text
    assert "Stop. Run no further squashes" in text

    only_parked = "mxxluvkm\thandoff/backend\tsection previews\n"
    text = warning("jj squash --into abc a.ts", None,
                   lambda a, c: "" if "working_copies" in a[1] else only_parked)
    assert "Not yours to fix" in text, text
    assert "Stop. Run no further squashes" not in text

    assert warning("jj squash --into xykttnxu a.ts", None, lambda a, c: "") is None
    assert warning("jj log -r 'conflicts()'", None, fake) is None
    print("ok")


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv else main())
