---
name: findings-report
description: Publish investigated findings (bugs, root causes, audit results, review notes) as one HTML Artifact in the daniel-artifact style — per-finding sections, verbatim code blocks with file:line headers, an at-a-glance index, and a severity/effort table. Use when the user asks to write up findings, turn investigations into a report or artifact, or produce a triage, bug or audit page.
---

# Findings report

Turns completed investigations into one reference page an engineer can work
from. The reader can fix the bug from this page without the transcript.

The findings must already exist. This skill formats and publishes. If the
investigations have not run, run them first (one subagent per finding is the
usual shape), then come back here.

## Steps

1. **Collect the findings into one Markdown file** in the scratchpad, one
   section per finding, before writing any HTML. Subagent reports go in
   verbatim, so code snippets survive byte for byte.
2. **Load `daniel-artifact`.** It owns the style: tokens, fonts, sizes,
   spacing, Light / Dark switch, chips. Load `artifact-diagramming` too if a
   finding has a causal chain worth drawing.
3. **Copy `<SKILL_DIR>/assets/template.html`** to the scratchpad. It is
   daniel-artifact's `base.html` with the findings components added under
   `/* page */`. Replace the ALL-CAPS placeholders and repeat the component
   blocks per finding. Consecutive reports read as the same document, so keep
   its CSS as it is.
4. **Publish with the Artifact tool.** A 2–4 word `<title>`, a one-sentence
   `description`, and `icon` "bug" for bugs, "search" for audits, "code" for
   reviews. Give the user the URL.

## Content rules

- **Code is verbatim.** Escape `<` `>` `&` and nothing else. Every block
  carries its `path:line-range` in the `.file` header.
- **Root cause first**, in the `.callout.crit` at the top of each section: the
  mechanism in one or two sentences, naming the function or field that fails.
  The evidence follows.
- **Keep everything the investigation found**: caveats, parity risks, test
  gaps, rejected fixes and the evidence against them.
- **Say what was rejected and why**, so the reader does not walk into the
  same dead end.
- **Mark scope honestly.** A finding that only reproduces under a flag, a
  config or a code path says so in its tags and in the table. A known
  incomplete migration reads as that, not as breakage.
- **Name the connecting theme once**, in the standfirst.
- **Diagram only a chain prose cannot carry**: a multi-hop cause, or two
  findings that share one shape. Lists stay lists.
- **Chips** for names the reader must spot again across findings (services,
  tables, types), via `chip(name)` from the base.

## Structure

Header (title, mono scope line, finding nav, theme switch) → eyebrow,
standfirst, meta row → at-a-glance rows linking to each section → severity and
effort table → cross-cutting callout → one `section.issue` per finding →
footer that states what was and was not examined.

Per finding: ordinal, symptom heading, tags (`.fl crit|warn|ok`) → root cause
callout → optional figure → numbered mechanism steps with code blocks → data
flow → rejected fixes → the fix as a diff (`.add` / `.del`) → why it is safe,
behaviour deltas, regression check → "Skipped" callout.

## Constraints

- No highlighter library. The `.add` / `.del` / `.cmt` / `.hl` spans are the
  highlighting.
- No `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` tags. The `<title>` tag is
  expected.
- **SVG cannot take `var()` in presentation attributes.** Use the `.s-*` /
  `.f-*` classes (`s-ink s-crit s-acc`, `f-ink f-muted f-crit f-acc`), so
  strokes follow the theme.
- Code blocks, tables and figures scroll inside their own container. The page
  has no sideways scroll.
