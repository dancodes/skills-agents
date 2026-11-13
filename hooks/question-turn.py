#!/usr/bin/env python3
"""Remind Claude that a question gets an answer, not work."""
import json
import re
import sys

QUESTION = re.compile(r"\?\s*$|^\s*(?:question\b|explain|what|why|how|is|are|does|do|where|which|when|who)\b", re.I)
REQUEST = re.compile(r"^\s*(?:can|could|would|will) you\b|^\s*please\b", re.I)
NOTE = (
    "This prompt looks like a question. If it is one, answer it: read files, "
    "but run no tests, builds, benchmarks or scratch code, and change nothing. "
    "Propose the work and wait for a go."
)
HOLD = re.compile(
    r"\b(?:don'?t|do not)\s+(?:do anything|start|act|execute|make (?:the |any )?changes?"
    r"|change anything|fix anything|touch anything)\b"
    r"|\b(?:plan only|answer only|just asking|re-?state the plan|repeat the plan)\b",
    re.I,
)
HOLD_NOTE = (
    "The user said not to start yet. Change no files and run no jj or git "
    "write, test, build or benchmark. Reply with the answer or the plan only. "
    "A changed plan is not a go: wait for an explicit go."
)


def note(prompt):
    if HOLD.search(prompt):
        return HOLD_NOTE
    return NOTE if QUESTION.search(prompt) and not REQUEST.search(prompt) else None


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    text = note(event.get("prompt") or "")
    if text:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": text,
        }}))
    return 0


def test():
    assert note("why does the cache miss?") == NOTE
    assert note("explain the park script") == NOTE
    assert note("what happens here\n\nfoo.py line 3") == NOTE
    assert note("is this right? fix it") == NOTE
    assert note("can you run it?") is None
    assert note("fix the conflict") is None
    assert note("/daniel add a toggle") is None
    assert note("question: does this slow loading") == NOTE
    assert note("dont make the change yet, show me the plan") == HOLD_NOTE
    assert note("ok lets write down tasks, dont do anything yet:") == HOLD_NOTE
    assert note("frontend only. dont start yet. repeat the plan to me") == HOLD_NOTE
    assert note("verify and come back with a cause. dont fix anything yet") == HOLD_NOTE
    assert note("can you check it? answer only") == HOLD_NOTE
    assert note("start the dev server") is None
    print("ok")


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv else main())
