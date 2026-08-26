#!/usr/bin/env python3
"""Block the Bash commands that break a parallel /daniel run.

Matches the command text directly rather than through an `if: "Bash(x:*)"`
filter. That filter uses the permission-rule matcher, which cannot prove what a
command containing $(...) expands to and matches conservatively, so every rule
fired on any command using command substitution.
"""
import json
import re
import sys

RULES = [
    (r"\bjj\s+op(?:eration)?\s+restore\b",
     "jj op restore is forbidden: it rewinds the whole repo operation log, "
     "which un-registers the workspaces other agents are working in. Correct "
     "your work forward with another squash, or apply the inverse of one named "
     "operation with jj op revert <operation-id>."),
    (r"\bjj\s+(?:undo|redo)\b",
     "jj undo and jj redo are forbidden: they take no target and act on "
     "whichever operation landed last in this shared repository, which is "
     "usually another agent's. Correct your work forward with another squash, "
     "or apply the inverse of one named operation with jj op revert "
     "<operation-id>, taking the id from jj op log."),
    (r"\bjj\s+op(?:eration)?\s+revert\b(?![^;&|]*\b[0-9a-f]{4,}\b)",
     "jj op revert with no operation id defaults to @, the newest operation in "
     "this shared repository, which is usually another agent's. Pass the id of "
     "your own operation, read from jj op log."),
    (r"\bjj\s+diff\b(?![^;&|]*(?:--git|--summary|--stat|--name-only|--types|(?:^|\s)-s(?=\s|$)))",
     "jj diff must be run with --git. Its default format cannot be pasted as a "
     "unified-diff hunk, which is what the report has to contain. Use jj diff "
     "--git <path>, or --summary/--stat/--name-only when you only need the list "
     "of files."),
    (r"\byarn\s+vitest\b",
     "yarn vitest is forbidden. Run the repository scripts instead: yarn test, "
     "or yarn test:integration for integration tests."),
    (r"\bnpx\b",
     "npx is forbidden. Use executables already present in the working "
     "directory (yarn scripts, ./node_modules/.bin) instead."),
]


def denial(command):
    for pattern, message in RULES:
        if re.search(pattern, command):
            return message
    return None


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    message = denial((event.get("tool_input") or {}).get("command", ""))
    if not message:
        return 0
    print(message, file=sys.stderr)
    return 2


def test():
    assert denial("jj op restore abc") == RULES[0][1]
    assert denial("jj undo") == RULES[1][1]
    assert denial("jj redo") == RULES[1][1]
    assert denial("jj op revert") == RULES[2][1]
    assert denial("jj op revert --what repo") == RULES[2][1]
    assert denial("jj op revert 197d348a40f5") is None
    assert denial("jj operation revert d79d4492643c --what repo") is None
    assert denial("jj diff") == RULES[3][1]
    assert denial("jj diff -r @ src/a.ts") == RULES[3][1]
    assert denial("jj diff --git src/a.ts") is None
    assert denial("jj diff --summary -r 'ws@'") is None
    assert denial("jj diff --name-only") is None
    assert denial("jj diff -s") is None
    assert denial("yarn vitest run foo") == RULES[4][1]
    assert denial("npx tsc") == RULES[5][1]
    # The regression these rules used to hit: substitution is not a match.
    assert denial("jj workspace add $(pwd)/../daniel-workspaces/feature") is None
    assert denial("ws=$(pwd)/x; for f in $ws/*; do echo $f; done") is None
    assert denial("yarn test:integration") is None
    assert denial("jj op log") is None
    assert denial("jj squash --into xykttnxu -u src/a.ts") is None
    print("ok")


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv else main())
