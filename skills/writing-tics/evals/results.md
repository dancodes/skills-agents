# Eval results

Light pass, 2026-11-10. Each eval input was edited by following SKILL.md and references/tics.md (done inline by the skill author, not by an independent subagent, so treat the pass rate as a sanity check). Programmatic checks ran with `python check_output.py evals.json <id> <output>`; the semantic assertions in `expectations` were graded by reading the outputs.

| Eval | Iteration 1 | Iteration 2 |
|------|-------------|-------------|
| 1 context-window-eval-report | 8/8 expectations, but see note | 8/8, 30/30 checks |
| 2 channel-conversion-analysis | 8/8 | 8/8 (unchanged) |
| 3 training-divergence-postmortem | 8/8 | 8/8 (unchanged) |
| 4 pr-description-backoff | 8/8 | 8/8 (unchanged) |
| 5 clean-temperature-results | 3/3, returned unchanged | 3/3 (unchanged) |

Note on iteration 1: the eval 1 output rewrote "Median hides it." as "The median latency does not reflect the slow requests at 128k." That swaps the verb but keeps the statistic as the actor, so it is still abstraction agency. The reference example ("The median latency understates the slow requests") had the same flaw. Changes made: the abstraction-agency rewrite guidance in references/tics.md now says to change the subject rather than the verb and has a new example; SKILL.md's "Name the concrete subject" rule says the same; eval 1 gained a regex check for statistic-as-agent verbs and an updated expected output. Iteration 2 of eval 1 passes all checks.
