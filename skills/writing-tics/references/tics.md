# Tic catalogue

Each entry has a definition, detection cues, look-alikes that are not the tic, and a before/after rewrite. The first example under each "Source example" is the one from the original tic table. The rewrites follow the hard rules in SKILL.md: same information, no new claims, no other tic, no em dashes, no fragments.

Contents:
1. Negation-first reveal
2. Significance designation
3. Abstraction agency
4. Deferred noun
5. Coy or thesis-shaped header
6. Aphoristic closer
7. Straw-man knockdown
8. Fragment cadence
9. Dressed metaphor
10. Label-first framing
11. Combined example

---

## 1. Negation-first reveal

**Definition.** The writer states what something is not and then, as a separate beat, what it is, so the reader meets a rejected option before the actual claim.

**Detect.**
- Two consecutive short sentences: "It is not X. It is Y." / "This isn't X. It's Y." / "That wasn't X. It was Y."
- The same shape joined by a colon, semicolon or dash: "not X; it is Y", "not X: Y".
- "Not X. Y." at the start of a paragraph, or "Not because X. Because Y."
- "X is not about A. It is about B."

**Not the tic.** A plain negative fact that answers a real question ("The fix did not change latency."). A single sentence that states the positive claim first and adds the contrast after it ("The cause was the data, not the learning rate.") is fine when the contrast carries information.

**Rewrite.** Lead with the positive claim. Keep the rejected option only if it tells the reader something (for example, that a wrong answer would have been scored differently), and attach it to the same sentence with "rather than", "instead of" or "not".

- Source example. Before: "It is not a wrong answer. It is a non-answer."
  After: "The response gives no answer at all, rather than a wrong one."
- Before: "It wasn't the learning rate. It was the data."
  After: "The data caused the divergence, not the learning rate."

---

## 2. Significance designation

**Definition.** The writer labels something as the important one ("the key", "the one that matters", "the leg that answers the actual question") instead of saying what it shows, so importance is asserted rather than demonstrated.

**Detect.**
- "is the one that matters", "is the leg/row/run/test that answers the (actual|real) question"
- "the real story", "the key finding", "the crucial part", "the part worth reading", "this is where it gets interesting"
- A sentence whose only content is that a named thing is important, followed by the content that would have made that obvious.

**Not the tic.** A ranking with a stated criterion ("Leg 6 has the largest drop, 13.3 points.").

**Rewrite.** Replace the designation with what the item shows or does. If the author's point is that this item is the main result, say so plainly and attach the concrete reason in the same sentence. Do not invent what "the actual question" was; use the text's own statement of it, or fall back to "main result".

- Source example. Before: "Leg 6 is the leg that answers the actual question. At 128k the model scores 61.2%."
  After: "The main result is leg 6: at 128k the model scores 61.2%."
- Before: "`sync_inventory()` is the one that matters: it runs every 5 minutes."
  After: "The bug affected `sync_inventory()`, which runs every 5 minutes."

---

## 3. Abstraction agency

**Definition.** An abstraction such as a statistic, table, chart, dataset, log or curve becomes the grammatical agent of a verb of perception, concealment or speech (hides, shows, tells, says, reveals, confirms, wants, refuses), often with a vague "it" as the object. The sentence points at a claim without making it.

**Detect.**
- Short sentences with an abstract subject and a pronoun object: "Median hides it." "The table shows it." "The logs confirm it." "The numbers don't lie."
- "The data tells a different story." "The curve tells the story." "The chart says otherwise."
- The sentence could be deleted and the paragraph would lose only rhythm.

**Not the tic.** Ordinary references that carry content: "Table 2 lists the per-seed scores." "The log records a timeout at 14:02." These name what is in the artifact.

**Rewrite.** State the fact directly with the concrete subject: the requests, the runs, the rows, the people. Swapping the verb is not enough. "The median understates it" or "The median does not reflect the slow requests" still makes the statistic the actor. If the point is that a statistic misleads, put the numbers side by side and let the sentence say what they are.

- Source example. Before: "Median hides it. The median request takes 2.1 s, but the p99 is 19.4 s."
  After: "Most requests are fast but a few are very slow: the median request takes 2.1 s, but the p99 is 19.4 s."
- Source example. Before: "The table shows it."
  After: state the claim the table supports, for example "Rows 3 to 5 all score below 60%."
- Before: "The logs confirm it. Gradient norm jumps from 0.9 to 14.2."
  After: "In the training logs, the gradient norm jumps from 0.9 to 14.2."

---

## 4. Deferred noun

**Definition.** The writer refers to an item by a count, ordinal or pronoun ("the sixth", "the other one", "one of them") and withholds its name, either until a later sentence or entirely. The reader has to hold a slot open.

**Detect.**
- An elliptical sentence built on a number word or ordinal with a bare verb: "The sixth is not." "The other one does." "Two of them don't."
- "One of these is different." followed later by which one.
- A count introduced before the items are named ("Five of those six rows are one cluster.").

**Not the tic.** Counts that are themselves the information ("All six legs finished."), and references whose item was named immediately before.

**Rewrite.** Name the item where it first appears and complete the elliptical verb. If the text never names it, describe it as fully as the text allows ("the other affected call site").

- Source example. Before: "Five of those six rows are one cluster. The sixth is not."
  After: "Rows 1 to 5 belong to one cluster, and row 6 does not." (If the rows are not numbered: "Five of the six rows belong to one cluster, and the remaining row does not.")
- Before: "Five channels convert between 11.8% and 12.9%. The sixth does not. Paid social converts at 4.3%."
  After: "Five channels convert between 11.8% and 12.9%, and the sixth, paid social, converts at 4.3%."

---

## 5. Coy or thesis-shaped header

**Definition.** A section header that teases the content, poses a question, or states the section's conclusion, instead of naming the topic.

**Detect.**
- Headers starting with What, Why, How, Where, When used as a teaser: "What 'exhausted' means", "Why the run diverged", "Where it breaks".
- Headers that assert a finding or contain evaluative words: "The one gap that does clear the bar", "What the numbers actually say", "The fix that wasn't".
- Words like "actually", "really", "the one", "that does", "turns out" in a header.

**Not the tic.** Plain topic labels ("Results", "Latency by context window"), and FAQ sections where the header is a real question readers ask.

**Rewrite.** A plain descriptive label naming what the section covers. Keep the markdown level.

- Source example. Before: `## What "exhausted" means` After: `## Definition of "exhausted"`
- Source example. Before: `## The one gap that does clear the bar` After: `## Gap above the significance threshold` (use the threshold's actual value if the section gives it)
- Before: `### Why the 7B run diverged` After: `### Cause of the 7B run divergence`

---

## 6. Aphoristic closer

**Definition.** A paragraph or section ends on a quotable generalization or moral, instead of on its specific point.

**Detect.**
- Last sentence of a paragraph that would make sense pasted into any other document.
- "It is the kind of X that looks like Y and is not." "That is the whole point." "Which is exactly the problem." "Bad data does not announce itself."
- Chiastic or paradoxical shapes, and second-person morals ("You can't fix what you don't measure.").

**Not the tic.** A closing sentence that states a specific conclusion, decision or next step.

**Rewrite.** Replace it with the specific claim it gestures at, using the paragraph's own numbers and names. If the paragraph already states that claim and the closer adds nothing, delete it. Keep any real content the closer carries, such as a verdict ("this is not evidence", "this is not a bug").

- Source example. Before: "It is the kind of number that looks like evidence and is not."
  After (with the paragraph's specifics): "The 3-point gain comes from a single run of 40 questions, so it is not evidence of an improvement."
- Before: "Bad data does not announce itself. It waits."
  After: "The bad shard caused no visible problem until training reached it." Or delete it if the paragraph already says so.

---

## 7. Straw-man knockdown

**Definition.** The writer introduces an interpretation that nobody in the context stated, labels it obvious or tempting, and rejects it, so the reader's attention goes to a position no one held.

**Detect.**
- "X is the obvious reading, and it is wrong." "The tempting conclusion is X. It's wrong."
- "You might think X." "It would be easy to assume X." "A naive reading says X."
- A quoted claim with no speaker, followed by a rejection.

**Not the tic.** Rebutting a position someone actually took (a reviewer, an earlier version of the doc, a named team), with attribution.

**Rewrite.** State the correct reading. If the wrong reading is a real risk for readers, keep it as a one-sentence caveat with its reason, without the "obvious" framing.

- Source example. Before: "\"It thinks twice as long\" is the obvious reading, and it is wrong."
  After: "The doubled token count does not mean the model thinks twice as long." (Then keep the author's next sentence, which usually gives the actual reason.)
- Before: "\"Paid social users are just lower intent\" is the obvious reading, and it is wrong. Paid-social users who finish onboarding convert at 12.4%."
  After: "Low intent does not explain the gap, because paid-social users who finish onboarding convert at 12.4%."

---

## 8. Fragment cadence

**Definition.** Verbless fragments in running prose, usually in a series, used for rhythm or emphasis.

**Detect.**
- Sentences with no finite verb: "Six legs." "No recovery." "One GPU, one server build, one sampler."
- Question-and-fragment pairs: "The result? A 13-point drop."
- Runs of two to four very short sentences in a row.

**Not the tic.** List items, table cells, headers, captions, `key: value` fields, code comments, and quoted speech. Leave those alone.

**Rewrite.** Merge the fragments into one or two full sentences with a subject and verb. Keep every item from the fragments, and keep what the repetition implied (for example, "one GPU, one server build" implies the legs share them).

- Source example. Before: "Six legs. One GPU, one server build, one sampler, one question set."
  After: "The run has six legs, and all six use the same GPU, server build, sampler and question set."
- Before: "Smooth descent to step 41,000, then a spike from 1.92 to 6.8 over 300 steps. No recovery."
  After: "The loss falls smoothly until step 41,000, then spikes from 1.92 to 6.8 over 300 steps and does not recover."

---

## 9. Dressed metaphor

**Definition.** A literal claim is dressed in a figurative image (costume, clothing, mask, tax, ghost, heavy lifting), so the reader has to translate the image back into the claim.

**Detect.**
- "X wearing the costume of Y", "X dressed up as Y", "X in Y's clothing", "X masquerading as Y"
- "a tax on", "doing the heavy lifting", "hiding in plain sight", "a ticking time bomb", "a promise you can't keep"
- Personification of a process or object outside abstraction agency ("the cache was lying to us").

**Not the tic.** Established technical terms that started as metaphors (memory leak, race condition, cold start, bottleneck, smoke test).

**Rewrite.** Say the literal claim. The usual shape is "X looks like Y but is actually X", or "X was treated as Y". Keep the specifics around it.

- Source example. Before: "That is information loss wearing the costume of a style fix."
  After: "That edit removes information, even though it was presented as a style fix."
- Before: "The 30% spend cut was a funnel problem wearing the costume of a targeting problem."
  After: "The team treated a funnel problem as a targeting problem and cut paid-social spend by 30%."

---

## 10. Label-first framing

**Definition.** A label, tag or coined name stands alone, as its own sentence or before a colon, ahead of the content it refers to. The reader gets the category before the claim, and coined names ("the sampler cliff") turn a finding into a brand.

**Detect.**
- A noun phrase as its own sentence or bold lead-in: "The fix." "The catch." "**The short version.**"
- Tag-and-colon openers in running prose: "The short version: X." "Bottom line: X." "Here's the thing: X." "The upshot: X."
- Coining a name and then using it: "Call it the sampler cliff." "This is the leg-4 problem."
- Source example: "The fucking left column of this table." This is a joke about the tic table itself: its left column is a list of coined labels, which is the habit the row names. In real text, the sign is a standalone emphatic noun phrase that points at something before saying anything about it.

**Not the tic.** Structured fields and conventions the author uses throughout a document (a status report with "Owner:", "Status:", "Next step:" lines), and terms the document defines and uses as real terminology.

**Rewrite.** Put the content first in a full sentence and drop the label. If the label carried meaning (that this is the fix, or a summary), fold it into the sentence ("This PR caps...", "In short, ..."). Keep the author's register, including profanity, if the sentence survives.

- Before: "**The fix.** `retry_with_backoff()` now caps the delay at 30 s."
  After: "This change makes `retry_with_backoff()` cap the delay at 30 s."
- Before: "The short version: onboarding step 2."
  After: "In short, the paid-social gap comes from step 2 of onboarding."
- Before: "The sampler cliff. Above temperature 0.9, accuracy drops from 71% to 52%."
  After: "Above temperature 0.9, accuracy drops from 71% to 52%."

---

## 11. Combined example

Before:

```
## What the numbers actually say

Six legs. One GPU, one server build, one sampler. Leg 6 is the leg that answers the actual question. It is not a gradual slide. It is a cliff.
```

After:

```
## Accuracy by leg

The run has six legs, and all six use the same GPU, server build and sampler. The main result is leg 6, where accuracy drops abruptly rather than gradually.
```

Every noun from the original (six legs, GPU, server build, sampler, leg 6, the abrupt drop) is still present, no new number or cause was added, and each new sentence has a subject and a verb.
