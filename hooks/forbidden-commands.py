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
    (r"\bjj\s+op\s+restore\b",
     "jj op restore is forbidden: it rewinds the whole repo operation log, "
     "which un-registers the workspaces other agents are working in. To back "
     "out your own last operation use jj undo."),
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
    assert denial("yarn vitest run foo") == RULES[1][1]
    assert denial("npx tsc") == RULES[2][1]
    # The regression these rules used to hit: substitution is not a match.
    assert denial("jj workspace add $(pwd)/../daniel-workspaces/feature") is None
    assert denial("ws=$(pwd)/x; for f in $ws/*; do echo $f; done") is None
    assert denial("yarn test:integration") is None
    assert denial("jj op log") is None
    print("ok")


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv else main())
