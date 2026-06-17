---
name: skill-evaluator
description: Evaluates and scores an existing Agent Skill against the agentskills.io spec and authoring best practices, then reports a grade and ranked fixes. Use when the user asks to review, audit, grade, lint, or quality-check a skill, find out why a skill doesn't trigger, or decide whether a skill is ready to ship. Input is a path to a skill directory.
---

# Skill Evaluator

## Overview
This skill takes an existing Agent Skill and tells you, with evidence, how good it is and exactly
what to fix. It combines a **static rubric** (structure, frontmatter, description quality, size,
script hygiene) with a **dynamic evaluation** (does it actually trigger, and does it change the
agent's behaviour versus no skill at all). Output is a grade plus a ranked list of concrete fixes —
not a vague "looks fine."

## When to Use
Use when the user wants to:
- review / audit / grade / lint / quality-check an existing skill;
- diagnose why a skill never triggers, or triggers on the wrong requests;
- decide whether a skill is ready to ship or needs another pass;
- compare two versions of a skill.

Do **not** use to *author* a new skill from scratch — that's the `skill-creator` skill. (Pair them:
create → evaluate → improve.)

## Inputs
- **Required:** a path to the skill directory to evaluate (the folder containing `SKILL.md`).
- **Optional:** a pass threshold (default grade B / ratio 0.8), and any existing eval prompts.

## Core Process

### 1. Locate and read the skill
Confirm the target directory contains a `SKILL.md`. Read the frontmatter and body, and note which
of `scripts/`, `references/`, `assets/` exist.

### 2. Run the static rubric
```
python scripts/score_skill.py <path/to/skill> --min 0.8
```
This is read-only and non-interactive. It prints a JSON report (data on stdout, logs on stderr) with
a 0–2 score on six dimensions — frontmatter validity, description trigger quality, progressive
disclosure/size, body concreteness, structure completeness, script hygiene — plus an overall grade
and priority fixes. Capture the JSON. Dimension definitions: `references/rubric.md`.

### 3. Read the static findings critically
The scorer uses heuristics, so confirm each flag by eye:
- Is the `description` genuinely third-person and does it say **when** (not just what)?
- Is the body lean (< 500 lines) with depth pushed into `references/`, or is it a wall of text?
- Are steps concrete and actionable, with **one default path** rather than a menu?
- Do bundled scripts avoid interactive prompts and route data→stdout / logs→stderr?

### 4. Run the dynamic evaluation (the part the script can't)
A high static score means "no obvious smell," not "proven good." Verify behaviour:
- **Trigger accuracy** — build ~15–20 labelled queries (should-trigger / should-NOT-trigger), run
  each 3× in fresh sessions, measure activation. Pass: should-trigger > 50%, near-miss < 50%.
- **Behaviour vs baseline** — run 2–3 realistic prompts with and without the skill; the skill earns
  its place only if it changes output, step count, or tokens. Grade on objective assertions.
- **Failure-mode probe** — pressure-test the excuses an agent makes to skip steps; confirm the
  skill's Rationalizations/Red Flags actually hold.
Method detail: `references/rubric.md` (Dynamic evaluation).

### 5. Report
Produce: the overall **grade**, the per-dimension static scores, the dynamic results (trigger rates
+ baseline delta), and **one ranked list of fixes, highest-impact first** — typically description
trigger quality, then behaviour delta, then size/bloat. Be specific: quote the offending line and
give the rewrite.

## Common Rationalizations
| The excuse | The reality |
|---|---|
| "It validated, so it's good." | The static rubric only proves the absence of obvious smells. Triggering and behaviour must be measured. |
| "I ran one prompt and it worked." | A single happy-path shot hides false-negatives and over-triggering. Use the labelled query set, 3× each. |
| "The skill is detailed, so it's thorough." | Length is a cost, not a virtue — long bodies cause context rot. Score size, and push depth into references/. |
| "No need for should-NOT-trigger cases." | Without near-misses you've only shown it *can* fire, not that it won't fire when it shouldn't. |

## Red Flags
- Reporting "looks fine" without running the static scorer **and** at least one baseline comparison.
- No should-NOT-trigger cases in the trigger test.
- Accepting a description that summarizes the workflow (it becomes a shortcut the agent follows instead of reading the skill).
- Treating a passing static grade as "ship it" without the dynamic checks.

## Verification
Deliver the evaluation only when:
- [ ] `score_skill.py` was run and its JSON is included in the report
- [ ] Every static flag was confirmed (or overridden) by reading the skill
- [ ] A trigger test with **both** should-trigger and should-NOT-trigger queries was run
- [ ] At least one baseline-vs-with-skill behavioural comparison was run
- [ ] The report ends with a single ranked, concrete fix list (quote → rewrite)

## Reference files
- `scripts/score_skill.py` — static rubric scorer (non-interactive, JSON on stdout).
- `references/rubric.md` — the six-dimension rubric, grade bands, and the dynamic-evaluation method.
