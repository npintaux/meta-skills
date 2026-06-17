# Skill Evaluation Rubric

The reference the `skill-evaluator` skill uses. Two halves: a **static** rubric (scored by
`scripts/score_skill.py`) and a **dynamic** evaluation (run by the agent, needs a live model).

## Static rubric — 6 dimensions, 0–2 each (max 12)
| Dimension | 2 (good) | 1 (weak) | 0 (broken) |
|---|---|---|---|
| Frontmatter validity | name kebab-case ≤64, matches folder, no reserved words; description ≤1024 | minor: name≠folder, >64, desc>1024 | name/description missing or illegal chars / reserved word |
| Description trigger quality | third person, states what + when, keyword-rich | missing one of: 3rd-person / when / keywords | empty |
| Progressive disclosure | body <400 lines, depth in references/ | 400–500, or >300 with no references/ | >500 lines |
| Body concreteness | numbered actionable steps, no vague verbs, one default path | some vagueness or menu-like | no step structure |
| Structure completeness | has When-to-Use + Verification | missing one | missing both |
| Script hygiene | non-interactive, data→stdout/logs→stderr | may mix logs into stdout | interactive prompt (will hang) |

Grade: A ≥0.9 · B ≥0.8 · C ≥0.7 · D ≥0.6 · F <0.6. Default pass threshold = 0.8 (B).

> The static scorer uses heuristics. A high score means "no obvious smell," not "proven good."
> A skill is only *proven* good by the dynamic tests below.

## Dynamic evaluation — the agent runs these (the part a script can't)
1. **Trigger accuracy.** Build ~15–20 labelled queries (should-trigger / should-NOT-trigger),
   run each 3× in fresh sessions, and measure activation. Target: should-trigger >50%,
   near-miss <50%. Report false-negatives and false-positives.
2. **Behaviour vs baseline.** Run 2–3 realistic prompts with and without the skill. The skill
   passes only if it changes output quality, step count, or token use. Grade on objective
   assertions where possible.
3. **Failure-mode probe.** Pressure-test the skill against the excuses an agent makes to skip its
   steps; confirm the Rationalizations/Red Flags actually hold.

## Output contract
Return: per-dimension static scores, the overall grade, the dynamic results (trigger rates +
baseline delta), and a single ranked list of concrete fixes — highest-impact first
(usually: description trigger quality > behaviour delta > size/bloat).
