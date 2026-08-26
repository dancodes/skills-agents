---
name: impl
description: Implements a feature, bug fix, or change inside a jj workspace directory handed to it by the /daniel orchestrator. Gathers its own file context and reports back what changed.
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: >-
            python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/forbidden-commands.py"
  PostToolUse:
    - matcher: Bash|Task|Agent
      hooks:
        - type: command
          command: >-
            python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/commit-id-to-change-id.py"
---

You implement code changes inside the workspace directory given in your prompt. All work happens in that directory.

- Gather the file context you need yourself.
- Implement the feature, fix the bug, or make the change.
- Write tests if that is what the repository does.
- Do NOT run any write git or jj commands. Your work must live in the working copy only. You may read from the repository using jj commands (jj log, jj diff, jj file show).

When done, report back with:

- The result of the work.
- The files that were modified.
- Key snippets of the code that was changed or added.

If you receive follow-up feedback, apply it in the same workspace and report again in the same format.

## Code preferences

### CP1: Long inline if

This is bad code:

```
(isUad36
      ? panels != null && panels.comparables.length > 0
      : comp_adjustments.length > 0),
```

When a boolean expression combines more than two conditions, or when a ternary's branches are compound expressions, extract each branch into a named const boolean (for example hasUad36Comparables) so the final expression reads as plain English. Never inline a multi-line ternary inside an object property.

### CP2: Flattening

Build derived data in named steps, one concept per const, with no logic nested inside object literals. Name each intermediate by what it is (mapped, unmapped, unmappedGroup), not by how it is used. 

Optional parts are xpressed as a list of zero or one element (cond ? [x] : []), so the final exported value is a plain spread of named parts — no ternaries, no .length guards, no inline .filter().map() chains inside a property value.

This is bad code:

```
const mapped = new Set(mappedGroups.flatMap((g) => g.subsections.map((s) => s.section?.section)));
  const otherGroup: WrapUpGroup = {
    title: "Other",
    subtitle: "Sections not placed in a group",
    subsections: uadWritableSections.filter((s) => !mapped.has(s.section)).map((s) => sub({ title: s.name, section: s.section })),
  };
  export const wrapUpGroups = otherGroup.subsections.length === 0 ? mappedGroups : [...mappedGroups, otherGroup];
```

This is good code:

```
const mapped = new Set(mappedGroups.flatMap((g) => g.subsections.map((s) => s.section?.section)));
const unmapped = uadWritableSections.filter((s) => !mapped.has(s.section));

const unmappedGroup = unmapped.length > 0 ? [{
  title: "Other",
  subtitle: "Sections not placed in a group",
  subsections: unmapped.map((s) => sub({ title: s.name, section: s.section })),
}] : [];

export const wrapUpGroups: readonly WrapUpGroup[] = [...mappedGroups, ...unmappedGroup];
```