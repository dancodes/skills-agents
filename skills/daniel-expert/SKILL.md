---
name: daniel-expert
description: Turn a task or prompt into a deeper one by asking what a top professional in the field would do, then rewrite the prompt to ask for exactly that. Use when the user invokes /daniel-expert, or asks for a deeper version of a task, an expert version of a prompt, or what a pro would do differently.
---

# /daniel-expert

Input: `/daniel-expert <task or prompt>`. With no argument, use the task or
prompt from the conversation so far.

The user wants a deeper version of the task, not a bigger one. Do not add
scope. Go further into the same task.

## Steps

Answer each question for this task and this field. Name the field first.

1. **What would a top professional do here that the user is not asking for?**
2. **What is the rawest material they would start from?** Name it instead of
   the summary, report or digest the user already has. Say where it lives.
3. **Which specific methods and tools would they use?** Name them. No
   generic advice like "research thoroughly".
4. **What, other than you or the user, would show the result is right?** Name
   an outside check: a test, a measurement, a source, a person, a benchmark.

Then **rewrite the user's prompt** to ask for exactly that. Put it in one
code block so it can be copied.

## Rules

- Each answer is specific to this task. A line that fits any task is cut.
- Keep the user's goal. Change how it is done, not what it is for.
- When the task is in a repo, read the relevant files before answering, so
  the raw material and tools are the real ones.
- Do not run the rewritten prompt. Stop after showing it.
- Short sentences, one idea each.
