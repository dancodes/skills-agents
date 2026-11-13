---
name: writing-tics
description: Removes ten specific writing tics from prose (negation-first reveals, significance designations, abstraction agency, deferred nouns, coy or thesis-shaped headers, aphoristic closers, straw-man knockdowns, fragment cadence, dressed metaphors, label-first framing) while keeping every fact, number, name and caveat. Use this skill whenever the user asks to de-tic, clean up, tighten, de-AI, or edit prose for these patterns, says "remove writing tics" or "make this read less like AI", or pastes a report, analysis, eval write-up, PR description or doc and asks for it to sound less AI-written or less punchy, even if they do not name the tics.
---

# Writing tics

This skill edits prose to remove ten rhetorical habits that make technical writing read as performed rather than plain. The goal is a narrow edit: find the tics, rewrite only the sentences that contain them, and leave everything else exactly as the author wrote it.

These tics matter because they hide content. A sentence like "Median hides it." or "Six legs." sounds crisp but makes the reader reconstruct the actual claim. A careless fix makes this worse by dropping the specifics the tic was pointing at. One of the tics' own examples names the failure: "information loss wearing the costume of a style fix." A rewrite that reads better but loses a number, a name or a caveat has failed.

## The ten tics

Read `references/tics.md` before editing. It has, for each tic, a definition, concrete detection cues, edge cases that are not the tic, and a before/after rewrite. The quick list:

| # | Tic | One-line definition | Typical surface cue |
|---|-----|---------------------|---------------------|
| 1 | Negation-first reveal | Says what something is not, then what it is, as two beats. | "It is not X. It is Y." / "This isn't X; it's Y." / "Not X. Y." |
| 2 | Significance designation | Announces that something is the important one instead of saying what it shows. | "the one that matters", "the leg that answers the actual question", "the real story" |
| 3 | Abstraction agency | An abstraction (median, table, data, logs, curve) is the agent of a verb like hides, shows, tells, says, confirms. | "Median hides it." / "The table shows it." / "The logs confirm it." |
| 4 | Deferred noun | Refers to an item by count, ordinal or pronoun and withholds or delays naming it. | "The sixth is not." / "The other one does." / "One of them is different." |
| 5 | Coy or thesis-shaped header | A header that teases, asks, or states a conclusion instead of labelling the section. | "What X means", "Why it broke", "The one gap that does clear the bar" |
| 6 | Aphoristic closer | A paragraph ends on a quotable generalization instead of the specific point. | "the kind of X that looks like Y and is not", "That is the whole point." |
| 7 | Straw-man knockdown | Raises a reading nobody stated in order to reject it. | "X is the obvious reading, and it is wrong." / "You might think X. You'd be wrong." |
| 8 | Fragment cadence | Verbless fragments used for rhythm in running prose. | "Six legs. One GPU, one server build." / "No recovery." |
| 9 | Dressed metaphor | A literal claim dressed in figurative clothing. | "wearing the costume of", "dressed up as", "in X's clothing", "a tax on" |
| 10 | Label-first framing | A label or coined name stands alone ahead of the content it refers to. | "The fix." / "The short version: X." / "Call it the sampler cliff." |

## How to edit

1. **Inventory the specifics first.** Before changing anything, note every number, unit, percentage, name, identifier, code span, link, date, hedge ("may", "about", "so far") and caveat in the text. Each one must appear in the output with the same meaning. This is the main safeguard against the information-loss failure above.

2. **Find the tics.** Go through the text sentence by sentence and header by header against the ten patterns. Treat a match as a tic only when it is doing rhetorical work in running prose. The reference file lists the look-alikes to leave alone.

3. **Rewrite only the affected sentences.** For each tic, write plain declarative sentences that name the concrete subject. Merge fragments into full sentences rather than deleting them, so the facts they carried survive. Sentences without tics stay byte-for-byte unchanged, including their punctuation and capitalization.

4. **Check the rewrite against the hard rules below.** Fixing one tic often creates another (a negation-first reveal becomes a straw-man; a fragment becomes a label). Re-read every sentence you changed against all ten patterns.

## Hard rules for rewrites

- **Keep all information and meaning.** Every specific from step 1 survives. Do not add claims, causes, numbers or interpretations the author did not make. If a tic hides a claim (for example "The table shows it." with no stated "it"), recover the claim from the surrounding text; if the text does not contain it, keep the sentence's meaning with the most literal wording available rather than inventing one.
- **Do not introduce another tic from the list.** Check each new sentence against all ten.
- **No em-dash swaps.** Do not replace a tic with an em dash or a spaced hyphen construction ("Not a wrong answer -- a non-answer."). Changing the punctuation between the two halves of a tic (period to colon, semicolon or dash) does not remove the tic. Use a full sentence with a verb, or a conjunction such as "because", "but", "so" or "rather than".
- **No sentence fragments.** Every sentence you write has a subject and a finite verb.
- **Name the concrete subject.** Prefer "The p99 latency at 128k is 19.4 s" over "It is slow" or "The data shows it is slow". When fixing abstraction agency, change the subject, not just the verb: "The median does not reflect the slow requests" still has the statistic acting.
- **Headers become plain descriptive labels** that name what the section covers: "Accuracy by context window", "Definition of 'exhausted'", "Gaps above the 2-point threshold". Keep the header level and markdown syntax.

## What to leave alone

- **Text with no tics.** If a passage has none of the ten patterns, return it unchanged. Do not rewrite for general style, concision, word choice or grammar preferences. This skill is not a general copy edit.
- **The author's voice and register.** Keep their vocabulary, tone, person ("we", "I"), tense, profanity, British or American spelling, and level of formality. A casual Slack post stays casual.
- **Formatting.** Keep markdown, header levels, list structure, tables, bold and italics that are not part of a tic, code blocks, inline code, links and line breaks. List items, table cells, captions and `key: value` fields are conventionally verbless; they are not fragment cadence.
- **Quotations and code.** Never edit quoted material, code or command output, even if it contains a tic.
- **Existing punctuation.** If the author already uses em dashes in sentences without tics, leave those sentences alone. The no-em-dash rule applies to your rewrites.

## Output

Return the edited text only, in the same format as the input (a markdown passage comes back as markdown), with no preamble or commentary. If the text had no tics, return it unchanged; you may add one short line saying no tics were found only if the user's request suggests they expect a report.

If the user asks what changed, add a short list after the edited text: one line per change, naming the tic and quoting the original fragment, for example `- Negation-first reveal: "It wasn't the learning rate. It was the data."`.

If the user asks to edit a file, edit it in place with the same rules and then report the list of changes.
