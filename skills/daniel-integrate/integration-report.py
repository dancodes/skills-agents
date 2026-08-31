#!/usr/bin/env python3
"""Print the evidence needed before and after an integration run.

The plan report delegates per-file ownership to handoff-owners.py. The verify
report keeps the post-squash checks together and bounds repetitive output.
"""
import argparse
import subprocess
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

DEFAULT_ROOT = "trunk()"
MAX_LINES = 20
OWNER_REPORT = Path(__file__).resolve().with_name("handoff-owners.py")


def jj(args):
    result = subprocess.run(
        ["jj", "--ignore-working-copy", "--color=never"] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"jj {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout


def parked():
    return jj([
        "bookmark",
        "list",
        "-r",
        'bookmarks(glob:"handoff/*")',
        "-T",
        'name ++ "\\n"',
    ]).split()


def branch_template():
    return 'change_id.shortest() ++ "  " ++ description.first_line() ++ "\\n"'


def bookmark_template():
    return (
        'change_id.shortest() ++ " [" ++ bookmarks ++ "] " '
        '++ description.first_line() ++ "\\n"'
    )


def block(title, text, limit=None):
    print(f"== {title} ==")
    lines = text.rstrip("\n").splitlines()
    if limit is not None and len(lines) > limit:
        lines = lines[:limit] + [f"... {len(lines) - limit} more lines"]
    print("\n".join(lines) if lines else "(none)")
    print()


def owner_report(handoffs, root):
    command = [sys.executable, str(OWNER_REPORT)] + handoffs + ["--root", root]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def plan(handoffs, root):
    handoffs = handoffs or parked()
    if not handoffs:
        print("Nothing parked: no handoff/* bookmark exists.")
        return 0

    branch = f"{root}..@"
    block(
        f"branch {branch}",
        jj(["log", "-r", branch, "--no-graph", "-T", branch_template()]),
    )
    for handoff in handoffs:
        block(
            f"handoff {handoff}",
            jj(["log", "-r", handoff, "--no-graph", "-T", bookmark_template()]),
        )
        block(
            f"{handoff} files",
            jj(["diff", "--summary", "-r", handoff]),
            MAX_LINES,
        )

    block("ownership, draft commands and blast radius", owner_report(handoffs, root))
    block("workspaces", jj(["workspace", "list"]))
    for handoff in handoffs:
        block(f"{handoff} diff", jj(["diff", "--git", "-r", handoff]))
    return 0


def verify(handoffs, targets, root):
    branch = f"{root}..@"
    for target in targets:
        target_log = jj(["log", "-r", target, "--no-graph", "-T", bookmark_template()])
        target_rows = target_log.splitlines()
        if len(target_rows) != 1:
            raise RuntimeError(
                f"target {target!r} resolved to {len(target_rows)} commits; "
                "pass one change ID or a narrower revset"
            )
        block(f"target {target}", target_log)
        block(
            f"target {target} diff stat",
            jj(["diff", "--stat", "-r", target]),
            MAX_LINES,
        )

    for handoff in handoffs:
        handoff_log = jj(["log", "-r", handoff, "--no-graph", "-T", bookmark_template()])
        block(f"bookmark {handoff}", handoff_log, 3)
        block(
            f"handoff {handoff} remainder",
            jj(["diff", "--summary", "-r", handoff]),
            MAX_LINES,
        )
    feature_conflicts = jj([
        "log",
        "-r",
        f"conflicts() & ({branch})",
        "--no-graph",
        "-T",
        bookmark_template(),
    ])
    all_conflicts = jj([
        "log",
        "-r",
        "conflicts()",
        "--no-graph",
        "-T",
        bookmark_template(),
    ])
    scaffolding = jj([
        "log",
        "-r",
        f'{branch} & (files(glob:"**/node_modules/**") | '
        'files("frontend/src/modules/api/generated"))',
        "--no-graph",
        "-T",
        bookmark_template(),
    ])
    block("feature-line conflicts", feature_conflicts, MAX_LINES)
    block("all conflicts", all_conflicts, MAX_LINES)
    block("scaffolding in feature line", scaffolding, MAX_LINES)
    block(
        "branch shape",
        jj(["log", "-r", branch, "--no-graph", "-T", branch_template()]),
        MAX_LINES,
    )
    return 1 if feature_conflicts.strip() or scaffolding.strip() else 0


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    subcommands = result.add_subparsers(dest="command", required=True)

    plan_parser = subcommands.add_parser(
        "plan", help="collect pre-integration evidence"
    )
    plan_parser.add_argument("handoffs", nargs="*", help="handoff bookmarks")
    plan_parser.add_argument("--root", default=DEFAULT_ROOT, help="branch root revset")

    verify_parser = subcommands.add_parser("verify", help="collect post-integration checks")
    verify_parser.add_argument("--handoff", action="append", required=True, dest="handoffs")
    verify_parser.add_argument("--target", action="append", required=True)
    verify_parser.add_argument("--root", default=DEFAULT_ROOT, help="branch root revset")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "plan":
            return plan(args.handoffs, args.root)
        return verify(args.handoffs, args.target, args.root)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1


def test():
    global jj
    calls = []

    def fake(args):
        calls.append(args)
        if args[:2] == ["bookmark", "list"]:
            return "handoff/one\nhandoff/two\n"
        if args[0] == "log":
            return "abcd1234 [handoff/one] example\n"
        return "file.ts\n"

    jj = fake
    assert parked() == ["handoff/one", "handoff/two"]
    assert jj(["diff", "--summary", "-r", "handoff/one"]) == "file.ts\n"
    assert calls

    def verify_fake(args):
        if args[0] == "log":
            revset = args[args.index("-r") + 1]
            if "conflicts()" in revset or "files(" in revset:
                return ""
            return "abcd1234 [handoff/one] example\n"
        return ""

    jj = verify_fake
    with redirect_stdout(StringIO()):
        assert verify(["handoff/one"], ["target"], "trunk()") == 0
    print("ok")


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv else main())
