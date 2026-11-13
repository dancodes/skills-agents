---
name: daniel-fastcheck
description: Do a fast pass over a subject with 5 Sonnet agents in a workflow, one angle each, each on a small tool call budget. Use when the user invokes /daniel-fastcheck, or asks for a quick look, a fast check, or a fast pass over code, a question or a claim.
---

# /daniel-fastcheck

Input: the subject to explore or check. It can be a question, a claim, a file,
a feature or a diff. An optional `calls=<N>` sets the tool call budget per
agent. The default is 8.

1. Write 5 angles for the subject. Each angle is one sentence and looks at the
   subject in a different way. For a claim, make at least one angle try to
   prove the claim wrong.
2. Run the Workflow tool with `scriptPath` set to `fastcheck.workflow.js` in
   this skill's directory and `args`
   `{"task": "<subject>", "angles": ["<5 angles>"], "cwd": "<directory>", "calls": <N>}`.
   Omit `angles` to use the default angles. Omit `cwd` to use the current
   directory.
3. Merge the reports into one answer. Put facts that 2 or more agents found
   first. Mark a fact that only 1 agent found as unconfirmed. List what the
   agents did not get to.

Do not read the code yourself to fill gaps. Report the gaps.
