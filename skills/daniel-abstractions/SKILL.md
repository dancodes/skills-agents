---
name: daniel-abstractions
description: Plan a better abstraction for existing code as concepts only, from the highest level to the lowest, with no code written. Use when the user invokes /daniel-abstractions, or asks to plan, rethink or redesign an abstraction, module or split.
---

# /daniel-abstractions

Input: `/daniel-abstractions <target> [goal]`. The target is code: a file, a
module, a bookmark or a change. The goal says what the new abstraction must
favour, e.g. "minimal work done".

The output is a plan in prose. Write no code, no pseudo-code and no type
signatures. Change no files.

## Steps

1. **Read before you plan.** Read the target code whole, its callers, its
   docs and its tests. Trace one real request or call end to end. Note each
   job the code does, where it lives, and each rule that exists more than once.
2. **Write the plan from the highest level to the lowest.** Pick the levels
   that fit this target. Start with the question that changes the most, often
   whether the code needs to exist at all. Stop when lower levels no longer
   change the answer.
3. **End with the decisions.** List the decisions only the user can make.

## Rules

- Keep the security, data-loss and auth rules. A plan can move them, but it
  never drops them.
- Name real identifiers and files from the target code. Do not write a
  generic textbook design.
- Tie each change to a problem you found in step 1.
- Name each trade-off in one sentence.
- Bullets and short sentences, one idea each. No code blocks.

## Close

End with the "**What I need from you**" section. List one numbered item per
open decision. Put the decision that changes the most first.
