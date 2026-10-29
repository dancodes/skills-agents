#!/usr/bin/env python3
"""Deny jj git push until a passing check has run since the last edit or rewrite."""
import json
import re
import sys

PUSH = re.compile(r"\bjj\s+(?:[^\s|;&]+\s+)*?git\s+push\b")
CHANGE = re.compile(r"\bjj\s+(?:[^\s|;&]+\s+)*?(?:squash|rebase|resolve|new|edit|restore|absorb)\b")
CHECK = re.compile(r"\b(?:typecheck|tsc|test|tests|pytest|vitest|lint|tf-run-tests|tf-lint)\b")
EDITS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
MESSAGE = (
    "Push denied: no passing check ran after the last conflict edit or jj "
    "rewrite. Run the typecheck and the lint of the files you touched at the "
    "stack tip, in the foreground, after the last jj new, squash or rebase, "
    "then push in its own call. A simple fix is no exception."
)


def calls(lines):
    failed = set()
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "tool_result" and block.get("is_error"):
                failed.add(block.get("tool_use_id"))
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        content = (entry.get("message") or {}).get("content")
        if entry.get("type") != "assistant" or not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "tool_use":
                yield block.get("name"), (block.get("input") or {}).get("command", ""), block.get("id") in failed


def last(pattern, text):
    return max((match.end() for match in pattern.finditer(text)), default=-1)


def effect(command, failed):
    push = PUSH.search(command)
    text = command[:push.start()] if push else command
    change, check = last(CHANGE, text), last(CHECK, text)
    if check > change:
        return not failed
    return False if change >= 0 else None


def denial(command, lines):
    if not PUSH.search(command):
        return None
    checked = True
    for name, cmd, failed in calls(lines):
        state = False if name in EDITS else effect(cmd, failed) if name == "Bash" else None
        if state is not None:
            checked = state
    if effect(command, False) is False:
        checked = False
    return None if checked else MESSAGE


def main():
    try:
        event = json.load(sys.stdin)
        with open(event.get("transcript_path") or "") as transcript:
            lines = transcript.readlines()
    except (ValueError, OSError):
        return 0
    message = denial((event.get("tool_input") or {}).get("command", ""), lines)
    if not message:
        return 0
    print(message, file=sys.stderr)
    return 2


def test():
    def use(i, name, command=""):
        return json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": i, "name": name, "input": {"command": command}}]}})

    def result(i, error=False):
        return json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": i, "is_error": error}]}})

    push = "jj git push -b feat"
    assert denial("jj log", [use("1", "Edit")]) is None
    assert denial(push, []) is None
    assert denial(push, [use("1", "Edit")]) == MESSAGE
    assert denial(push, [use("1", "Bash", "jj squash -u"), result("1")]) == MESSAGE
    assert denial(push, [use("1", "Edit"), use("2", "Bash", "yarn typecheck"), result("2")]) is None
    assert denial(push, [use("1", "Edit"), use("2", "Bash", "yarn typecheck"),
                         result("2", error=True)]) == MESSAGE
    assert denial(push, [use("1", "Bash", "make test"), result("1"),
                         use("2", "Bash", "jj squash -u")]) == MESSAGE
    assert denial(push, [use("1", "Edit"), use("2", "Bash", "yarn test --run a.test.ts"),
                         use("3", "Bash", "jj log -r 'conflicts()'")]) is None
    assert denial(push, ["not json", use("1", "Bash", "jj new abc")]) == MESSAGE
    assert denial(push, [use("1", "Edit"), use("2", "Bash", "jj new abc && yarn typecheck && yarn lint"),
                         result("2")]) is None
    assert denial(push, [use("1", "Bash", "yarn typecheck && jj squash -u"), result("1")]) == MESSAGE
    assert denial("jj squash -u && jj git push -b feat", []) == MESSAGE
    print("ok")


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv else main())
