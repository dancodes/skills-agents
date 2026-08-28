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
    (r"\bjj\s+op(?:eration)?\s+abandon\b",
     "jj op abandon is forbidden: it discards operation history, and a "
     "workspace whose recorded operation is discarded goes stale. jj workspace "
     "update-stale then rebuilds that workspace as a recovery commit, which "
     "leaves the change divergent and makes the work look lost. Nothing here "
     "needs to prune the operation log."),
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
    (r"\byarn\s+typecheck\b|\b(?:tsgo|tsc)\b",
     "Running the typechecker directly is forbidden. Every workspace on this "
     "machine shares its RAM, tsgo peaks around 4GB, and several at once "
     "thrash the machine until the OOM killer fires. Run\n\n"
     "    python3 \"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel/typecheck.py\"\n\n"
     "from the directory you would have typechecked in. It takes the same "
     "arguments, waits for its turn, and then runs yarn typecheck. Give the "
     "Bash call a timeout of 600000 so the wait cannot cut the run short."),
    (r"\bjj\s+new\b(?![^;&|]*--no-edit\b)",
     "jj new without --no-edit moves the working copy of whichever workspace it "
     "runs in, and workspaces here belong to other agents. To make room for a "
     "commit that has to be new, run\n\n"
     "    jj new --no-edit --insert-before @ -m \"<message>\"\n\n"
     "from the integration workspace: it creates the commit at the branch tip, "
     "rebases @ on top of it, and moves no working copy. Then squash the "
     "handoff's files into it."),
    (r"\bjj\s+(?:abandon|restore)\b",
     "jj abandon and jj restore are forbidden: both discard content that only "
     "exists in a working copy or a commit another agent is sitting on. Correct "
     "work forward with another squash instead."),
    (r"\bgit\s+stash\b",
     "git stash is forbidden. This repository uses jj, and stashing moves files "
     "out from under every other agent working here."),
]


EDIT = re.compile(r"\bjj\s+edit\b")
EDIT_MESSAGE = (
    "jj edit is forbidden in a /daniel workspace: it moves that workspace's "
    "working copy, and the workspace belongs to another agent. Work is parked "
    "with skills/daniel/park-workspace.sh and integrated by /daniel-integrate, "
    "neither of which needs to move a working copy. The integration workspace "
    "may run it, to sit on a conflicted commit and resolve it."
)


UPDATE_STALE = re.compile(r"\bjj\s+workspace\s+update-stale\b")
UPDATE_STALE_MESSAGE = (
    "jj workspace update-stale is forbidden in a /daniel workspace. It "
    "rewrites the files on disk to match a commit, so every edit made since "
    "the last snapshot is discarded, and it can leave the change divergent, so "
    "jj status and jj diff in this directory then report the empty side and "
    "the work looks lost. The workspace going stale is expected and harmless: "
    "it is deleted at cleanup. Read its content from the original workspace "
    "with jj diff --git -r '<workspace-name>@'. If the change is already "
    "divergent, name the side that holds the files with a change offset, "
    "<change-id>/0 for the most recent and /1 for the one before.\n\n"
    "Before anything else: copy every file you edited to your scratchpad "
    "directory. Edits that were never snapshotted exist only on disk, and the "
    "operation log cannot recover them. Then stop and report the stale state, "
    "naming the files you edited."
)


WORKSPACE_WRITE = re.compile(
    r"\bjj\s+(?:[^\s|;&]+\s+)*?(?:squash|rebase|split|absorb|backout|commit|new"
    r"|bookmark\s+(?:move|set|delete|forget|track|untrack)"
    r"|workspace\s+forget|git\s+(?:push|fetch))\b"
)
WORKSPACE_WRITE_MESSAGE = (
    "This command rewrites shared repository state from inside a /daniel "
    "workspace. Only the integration workspace may do that, and only under the "
    "/daniel-integrate lock: two squashes landing concurrently leave the change "
    "divergent and every other workspace stale, which is how work has been lost "
    "here before. An impl workspace parks its finished work with "
    "skills/daniel/park-workspace.sh, which describes the working-copy commit "
    "and marks it with a handoff/<workspace-name> bookmark, and then stops. "
    "/daniel-integrate squashes that bookmark into the feature line later."
)


def in_daniel_workspace(command, cwd):
    return "daniel-workspaces" in command + cwd


def denial(command, cwd=""):
    if UPDATE_STALE.search(command) and in_daniel_workspace(command, cwd):
        return UPDATE_STALE_MESSAGE
    if EDIT.search(command) and in_daniel_workspace(command, cwd):
        return EDIT_MESSAGE
    for pattern, message in RULES:
        if re.search(pattern, command):
            return message
    if WORKSPACE_WRITE.search(command) and in_daniel_workspace(command, cwd):
        return WORKSPACE_WRITE_MESSAGE
    return None


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    message = denial(
        (event.get("tool_input") or {}).get("command", ""),
        event.get("cwd", ""),
    )
    if not message:
        return 0
    print(message, file=sys.stderr)
    return 2


def test():
    assert denial("jj op restore abc") == RULES[0][1]
    assert denial("jj op abandon ..abc") == RULES[2][1]
    assert denial("jj workspace update-stale",
                  "/x/daniel-workspaces/feat") == UPDATE_STALE_MESSAGE
    assert denial("cd /x/daniel-workspaces/feat && jj workspace update-stale",
                  "/x/repo") == UPDATE_STALE_MESSAGE
    assert denial("jj workspace update-stale", "/x/repo") is None
    # jj edit resolves conflicts from the integration workspace, and only there.
    assert denial("jj edit xyz", "/x/daniel-workspaces/feat") == EDIT_MESSAGE
    assert denial("jj edit xyz", "/x/repo") is None
    assert denial("jj new") == RULES[8][1]
    assert denial("jj new -m 'x' --insert-before @") == RULES[8][1]
    assert denial("jj new --no-edit --insert-before @ -m 'feat: x'") is None
    assert denial("jj abandon xyz") == RULES[9][1]
    assert denial("jj restore src/a.ts") == RULES[9][1]
    assert denial("git stash") == RULES[10][1]
    assert denial("jj squash --into abc a.ts",
                  "/x/daniel-workspaces/feat") == WORKSPACE_WRITE_MESSAGE
    assert denial("jj bookmark delete handoff/feat",
                  "/x/daniel-workspaces/feat") == WORKSPACE_WRITE_MESSAGE
    assert denial("jj new --no-edit --insert-before @ -m 'x'",
                  "/x/daniel-workspaces/feat") == WORKSPACE_WRITE_MESSAGE
    assert denial("jj git push", "/x/daniel-workspaces/feat") == WORKSPACE_WRITE_MESSAGE
    # Parking is the one write an impl workspace makes, and it stays allowed.
    assert denial("jj describe -m 'feat: x'", "/x/daniel-workspaces/feat") is None
    assert denial("jj bookmark create handoff/feat -r @",
                  "/x/daniel-workspaces/feat") is None
    assert denial("jj status", "/x/daniel-workspaces/feat") is None
    # Integration runs from the integration workspace, so the same squash passes.
    assert denial("jj squash --from handoff/feat --into abc -u a.ts", "/x/repo") is None
    assert denial("jj undo") == RULES[1][1]
    assert denial("jj redo") == RULES[1][1]
    assert denial("jj op revert") == RULES[3][1]
    assert denial("jj op revert --what repo") == RULES[3][1]
    assert denial("jj op revert 197d348a40f5") is None
    assert denial("jj operation revert d79d4492643c --what repo") is None
    assert denial("jj diff") == RULES[4][1]
    assert denial("jj diff -r @ src/a.ts") == RULES[4][1]
    assert denial("jj diff --git src/a.ts") is None
    assert denial("jj diff --summary -r 'ws@'") is None
    assert denial("jj diff --name-only") is None
    assert denial("jj diff -s") is None
    assert denial("yarn vitest run foo") == RULES[5][1]
    assert denial("npx eslint .") == RULES[6][1]
    assert denial("yarn typecheck") == RULES[7][1]
    assert denial("yarn typecheck --watch") == RULES[7][1]
    assert denial("cd ../ws && yarn typecheck") == RULES[7][1]
    assert denial("./node_modules/.bin/tsgo --noEmit") == RULES[7][1]
    assert denial("yarn tsc -p .") == RULES[7][1]
    assert denial('python3 "$HOME/.claude/skills/daniel/typecheck.py"') is None
    assert denial(
        "TYPECHECK_SLOTS=2 python3 ~/.claude/skills/daniel/typecheck.py") is None
    assert denial("cat tsconfig.json") is None
    # The regression these rules used to hit: substitution is not a match.
    assert denial("jj workspace add $(pwd)/../daniel-workspaces/feature") is None
    assert denial("ws=$(pwd)/x; for f in $ws/*; do echo $f; done") is None
    assert denial("yarn test:integration") is None
    assert denial("jj op log") is None
    assert denial("jj squash --into xykttnxu -u src/a.ts") is None
    print("ok")


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv else main())
