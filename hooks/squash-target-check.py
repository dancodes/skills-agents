#!/usr/bin/env python3
"""Deny a jj squash whose target commit does not own the file being squashed.

Squashing a file into a commit that never touched it makes jj carry the content
forward through the descendants that do touch it, which conflicts and cascades
to every descendant, including the working copies other agents are sitting on.
The commit that already touches the file is the target.

Every jj call here is read-only and passes --ignore-working-copy: the /daniel
agents share one repository, and a snapshot from a hook firing on every Bash
call would rewrite the working-copy commit another agent is editing.
"""
import json
import re
import shlex
import subprocess
import sys

# Flags that consume the next token, so its value is never mistaken for a path.
VALUE_FLAGS = {
    "--into", "--from", "-r", "--revision", "-m", "--message", "--tool",
    "-R", "--repository", "--at-op", "--at-operation", "--config",
    "--config-file", "--color", "-T", "--template", "--what",
}
# -o/-A/-B create a new commit rather than moving content into an existing one,
# so the ownership question does not apply.
NEW_COMMIT_FLAGS = {"-o", "-A", "--insert-after", "-B", "--insert-before"}

ID_TEMPLATE = 'change_id.shortest(8) ++ "\\t" ++ description.first_line() ++ "\\n"'


def jj(args, cwd):
    try:
        result = subprocess.run(
            ["jj", "--ignore-working-copy", "--color=never"] + args,
            cwd=cwd or None, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def segments(command):
    return re.split(r"&&|\|\||[;\n|]", command)


def parse_squash(segment):
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return None
    while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
        tokens.pop(0)
    if not tokens or not (tokens[0] == "jj" or tokens[0].endswith("/jj")):
        return None
    tokens.pop(0)

    subcommand = None
    while tokens:
        token = tokens.pop(0)
        if token in VALUE_FLAGS:
            tokens and tokens.pop(0)
        elif token.startswith("-"):
            continue
        else:
            subcommand = token
            break
    if subcommand != "squash":
        return None

    sources, target, revision, paths = [], None, None, []
    while tokens:
        token = tokens.pop(0)
        name, _, inline = token.partition("=")
        value = inline if inline else (tokens.pop(0) if tokens and name in VALUE_FLAGS else None)
        if name in NEW_COMMIT_FLAGS:
            return None
        if name == "--from":
            sources.append(value)
        elif name == "--into":
            target = value
        elif name in ("-r", "--revision"):
            revision = value
        elif not token.startswith("-"):
            paths.append(token)

    if revision:
        sources = [revision]
    if not sources:
        sources = ["@"]
    if not target:
        target = sources[0] + "-"
    if None in sources or target is None:
        return None
    return sources, target, paths


def owners(target, sources, path, cwd, run):
    """Commits at or under `target` that touch `path`. The sources are excluded:
    they always touch it, since their content is what the squash moves."""
    excluded = " | ".join(f"({s})" for s in sources)
    fileset = path.replace("\\", "\\\\").replace('"', '\\"')
    out = run(["log", "--no-graph", "-T", ID_TEMPLATE,
               "-r", f'(({target}):: & files("{fileset}")) ~ ({excluded})'], cwd)
    if out is None:
        return None
    return [line.split("\t", 1) for line in out.splitlines() if line.strip()]


def denial(command, cwd, run=jj):
    for segment in segments(command):
        parsed = parse_squash(segment)
        if not parsed:
            continue
        sources, target, paths = parsed

        resolved = run(["log", "--no-graph", "-T", ID_TEMPLATE, "-r", target], cwd)
        if resolved is None or len(resolved.splitlines()) != 1:
            continue  # ambiguous or unresolvable target: jj will reject it itself
        target_id = resolved.split("\t", 1)[0]

        if not paths:
            listed = run(["diff", "--name-only", "-r", sources[0]], cwd)
            paths = listed.splitlines() if listed else []

        misplaced = []
        for path in paths:
            found = owners(target, sources, path, cwd, run)
            if found and not any(cid == target_id for cid, _ in found):
                misplaced.append((path, found))
        if misplaced:
            return message(target, target_id, misplaced)
    return None


def message(target, target_id, misplaced):
    lines = [f"Wrong squash target: {target_id} does not own these files."]
    for path, found in misplaced:
        lines.append(f"\n  {path}")
        for cid, description in found:
            lines.append(f"    owned by {cid}  {description or '(no description)'}")
    lines.append(
        f"\nSquashing a file into a commit that never touched it makes jj carry the\n"
        f"content forward through the descendants that do, which conflicts and\n"
        f"cascades to every descendant, including other workspaces' working copies.\n"
        f"Squash each file into the commit listed above it, one target per command."
    )
    return "\n".join(lines)


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool_input = event.get("tool_input") or {}
    text = denial(tool_input.get("command", ""), event.get("cwd"))
    if not text:
        return 0
    print(text, file=sys.stderr)
    return 2


def test():
    assert parse_squash("jj squash --from ws@ --into abc -u a.ts b.ts") == (["ws@"], "abc", ["a.ts", "b.ts"])
    assert parse_squash("jj squash --into=abc --from=ws@ a.ts") == (["ws@"], "abc", ["a.ts"])
    assert parse_squash("jj squash") == (["@"], "@-", [])
    assert parse_squash("jj squash -r xyz") == (["xyz"], "xyz-", [])
    assert parse_squash("jj -R /repo squash --into abc a.ts") == (["@"], "abc", ["a.ts"])
    assert parse_squash('jj squash --into abc -m "fix a.ts" b.ts') == (["@"], "abc", ["b.ts"])
    assert parse_squash("jj squash --into abc -A xyz") is None
    assert parse_squash("jj log -r abc") is None
    assert parse_squash("echo jj squash") is None

    branch = {
        # (target, path) -> the commits that own that path
        ("wrongtgt", "sections/disaster.ts"): [["righttgt", "wrap up disaster mitigation"]],
        ("righttgt", "sections/disaster.ts"): [["righttgt", "wrap up disaster mitigation"]],
        ("wrongtgt", "sections/preview.test.ts"): [],
    }

    def fake(args, cwd):
        if args[0] == "log" and "-r" in args:
            revset = args[args.index("-r") + 1]
            if "::" not in revset:
                return f"{revset}\tdescription of {revset}\n"
            target = revset.split(")::", 1)[0].lstrip("(")
            path = revset.split('files("', 1)[1].split('")', 1)[0]
            rows = branch.get((target, path), [])
            return "".join(f"{cid}\t{desc}\n" for cid, desc in rows)
        if args[0] == "diff":
            return "sections/disaster.ts\nsections/preview.test.ts\n"
        return None

    bad = denial("jj squash --from ws@ --into wrongtgt -u sections/disaster.ts", None, fake)
    assert bad and "righttgt" in bad and "wrap up disaster mitigation" in bad, bad
    assert denial("jj squash --from ws@ --into righttgt -u sections/disaster.ts", None, fake) is None
    assert denial("jj squash --from ws@ --into wrongtgt -u sections/preview.test.ts", None, fake) is None
    assert denial("jj squash --from ws@ --into wrongtgt -u", None, fake)
    assert denial("jj log -r wrongtgt", None, fake) is None
    assert denial("jj squash --into wrongtgt a.ts", None, lambda a, c: None) is None
    print("ok")


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv else main())
