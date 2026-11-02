---
name: daniel-changelog
description: Explain a set of commits three ways, in order - what each one changed, its before and after behavior, then a summary in Daniel's voice to post for a teammate (MR note, Slack). Use when the user invokes /daniel-changelog, or asks for a change summary, changelog or reviewer note for some commits.
---

# /daniel-changelog

Input: the commits to explain, as change IDs, a revset or a range. With no
input, use the commits this conversation made or reviewed.

Read each commit's diff and message before you write. Keep the commits in
commit order, oldest first. Give all 3 parts, in this order.

## 1. What changed

One item per commit: its short name and change ID, then 1 or 2 sentences on
what it changed and why.

## 2. Before and after

One item per commit, with 2 sub-lines:

- Before: what a user or client saw, with a concrete trigger and its outcome.
- After: what happens now. For a commit with no runtime change, say so.

## 3. Summary for reviewers

Write this part in Daniel's voice, not in Simplified Technical English:

- Open with one line, e.g. "Reviewed and added 5 commits on top:".
- One line per commit, in commit order. Two lines at most.
- Say what a user or client saw before and what happens now: name the
  trigger with a concrete example, then the outcome ("a Water utility with an
  electricity source was accepted, then 500'd on save; now a 422").
- Leave out the mechanism: no validator, class, enum or file names, no change IDs.
- Put a data change, such as a migration that deletes rows, on its own sub-line.
- Refer to an earlier item instead of repeating it ("Similar to the previous
  one, but on update").
- A commit with no behavior change gets two or three words ("Comment updates").
- Casual tone. No headings, no bold, no closing line.
