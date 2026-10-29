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
   job the code does and where each job lives. Note each rule that exists
   more than once.
2. **Write the plan, level by level.** Go from the highest level to the lowest.
   Stop at a level when the levels below it no longer change the answer.
3. **End with the decisions.** List the decisions only the user can make.

## Levels

Use these levels, in this order. Give each one a `##` heading.

- **Level 0: Does it need to exist?** Name the one goal that justifies the
  code. Say what replaces it if that goal goes. Say which known bugs that
  replacement would remove.
- **Level 1: The questions per call.** Reduce each call to a short numbered
  list of questions, in order. Each question gets one owner. Say where the
  current code mixes owners or repeats a rule.
- **Level 2: The modules.** Name each module and the one thing it knows.
  Say what each module must not know. If a module has one user, say why the
  split still earns its place, or merge it. Keep policy as plain data, not
  hooks.
- **Level 3 and down: Each module, smallest form.** For each module, list what
  it does on the way in, on the way out and on failure. Name the stdlib or
  existing helper that replaces hand-written code. Map each failure to one
  outcome. Name each trade-off in one sentence.
- **Delete.** List the code, checks, scripts and config that the new shape
  makes useless.
- **Tests.** Give one line per module: what to fake and what to check.

Keep the security, data-loss and auth rules. A plan can move them, but it
never drops them.

## Style

- Bullets and short sentences, one idea each.
- Name real identifiers and files from the target code. Do not write a
  generic textbook design.
- Tie each change to a problem you found in step 1, e.g. "one table cannot
  drift, so this fixes the extension mismatch".
- No code blocks.

## Close

End with the "**What I need from you**" section. List one numbered item per
open decision. Put the decision that changes the most levels first. Level 0
is often that decision.
