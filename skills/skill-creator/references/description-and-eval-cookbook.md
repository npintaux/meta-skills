# Description & Evaluation Cookbook

Deep reference for `skill-creator`. The agent reads this **only** when it reaches the
description-tuning or evaluation steps — keeping `SKILL.md` itself lean (progressive disclosure).

---

## 1. Writing a description that triggers

The `description` is the **only** thing the agent reads to decide whether to load your skill
(among potentially 100+). It must carry both halves:

- **WHAT** the skill does — one concrete capability.
- **WHEN** to use it — the real situations/phrases that should trigger it.

### Rules
1. **Third person.** `Generates…`, `Extracts…`, `Reviews…` — never "I", "you", "this skill".
2. **Lead with concrete triggers.** Name the file types, tools, verbs, and user phrases that
   should activate it. Keyword-rich beats elegant.
3. **Be assertive about triggering** without summarizing the whole workflow. (If the description
   restates the body's steps, the agent may follow the *summary* and skip reading the skill.)
4. **Keep it tight.** Hard limit 1024 chars; aim well under that. No XML/HTML tags.

### Examples
| Verdict | Description |
|---|---|
| ✗ weak | `Helps with PDFs.` |
| ✗ weak | `This skill is for testing. I will write tests for you.` |
| ✓ strong | `Extracts text and tables from PDF files. Use when the user uploads or references a .pdf and needs its contents, fields, or a data export.` |
| ✓ strong | `Generates pytest unit tests for Python modules. Use when the user asks to add or improve tests, mentions coverage, or points at a .py file lacking tests.` |

---

## 2. Building the trigger-evaluation set

Do **not** tune a description by feel. Build a labelled query set and measure.

Generate ~16–20 realistic queries, split into two halves (8–10 per side across the 4 quadrants):

- **should-trigger** (8–10): the messy, colloquial ways a user would ask for this skill.
  e.g. for a db-log skill: *"parse this db log file"*, *"why is my query slow, here's the log"*.
- **should-NOT-trigger** (8–10): near-misses with overlapping keywords but a different goal —
  these guard against false activation. e.g. *"write a db schema"*, *"fix my SQL syntax error"*.

### The 4-Quadrant Eval Framework
Structure your ~16–20 test queries across four distinct quadrants to ensure robust boundary testing:

1. **Quadrant 1 — Direct Triggers (canonical)**: Clear, explicit phrasings directly naming the capability (e.g. *"create an agent skill for PR reviews"*).
2. **Quadrant 2 — Colloquial Triggers (indirect)**: Conversational, synonym-rich requests without jargon (e.g. *"turn this repetitive terminal workflow into something the assistant can run"*).
3. **Quadrant 3 — Keyword Near-Misses (no-trigger)**: Share trigger keywords or domain vocabulary, but ask for a different task (e.g. *"improve my Python programming skill"*, *"evaluate this ML model benchmark"*).
4. **Quadrant 4 — Sibling / Adjacent Tasks (no-trigger)**: Legitimate requests that belong to a sibling skill or the base agent (e.g. *"audit this pull request"*, *"generate a test suite"*).

### Train / validation split (avoid overfitting)
- Put **60%** of each half in a **train** set you iterate the description against.
- Hold **40%** in a **validation** set you do **not** look at while editing.
- A description "passes" when, on the *validation* set, should-trigger queries fire **> 50%** of
  the time across repeated runs and should-NOT-trigger queries stay **< 50%**.
- Run each query **3×** (models are nondeterministic) and use the activation rate, not a single shot.

When a should-trigger query fails, fix the **category** (add the missing kind of phrasing), not the
one literal string — otherwise you overfit and break on the next paraphrase.

### Commit the set as `evals/trigger_evals.json`
The eval set is an **artifact**, not a throwaway you rebuild each session. Scaffold it with
`scripts/new_evals.py <skill-dir>`, then fill it in. Schema (parsed by `validate_skill.py` and
`score_skill.py`, both dependency-free):

```json
{
  "skill": "your-skill-name",
  "queries": [
    { "quadrant": "Q1_direct",           "query": "turn this workflow into a skill",        "expect": "trigger",    "split": "train" },
    { "quadrant": "Q2_colloquial",       "query": "make a reusable tool from this prompt",   "expect": "trigger",    "split": "val" },
    { "quadrant": "Q3_near_miss",        "query": "write a bash script to rename files",     "expect": "no-trigger", "split": "train", "note": "scripting, not skill authoring" },
    { "quadrant": "Q4_sibling_adjacent", "query": "grade this skill against the spec",       "expect": "no-trigger", "split": "val",   "note": "handled by skill-evaluator" }
  ]
}
```

Rules the validator enforces: at least one `trigger` **and** one `no-trigger` entry (a set with no
near-misses only proves the skill *can* fire, never that it won't over-fire); `TODO` placeholder rows
don't count as real queries. The scorer's `trigger_eval_coverage` dimension awards full marks at
~10+ real queries with both sides present. Running the queries stays agent-driven — no script can
spawn the fresh sessions trigger-testing needs; the files only prove the set *exists and is shaped right*.

---

## 3. Baseline-vs-with-skill behavioural test

A skill earns its place only if it **changes behaviour** versus no skill at all.

1. Pick 2–3 realistic task prompts.
2. Run each in a clean session **without** the skill → record output, step count, tokens. This is
   the baseline (and it usually reveals the exact corrections the skill must encode).
3. Run the same prompts **with** the skill active.
4. Define **objective assertions** where possible (`output is valid JSON`, `≤ 4 tool calls`,
   `ran the linter`), grade programmatically, and have a human spot-check the rest.
5. If with-skill ≈ baseline, the skill isn't pulling its weight — cut or sharpen it.

> "No skill without a failing test first." If you can't show the agent failing the task without the
> skill, you don't yet know what the skill is for.

---

## 4. Match the form to the failure

Pick the body shape that fits *how the task fails*, instead of defaulting to prose:

| Failure mode | Use this shape |
|---|---|
| Agent cuts corners / skips a step | Prohibition + **Rationalizations table** (excuse → rebuttal) + **Red Flags** |
| Output is the wrong shape | A positive **recipe / contract** + a concrete template to copy |
| Agent omits a required element | A **REQUIRED structural slot** it must fill |
| Behaviour depends on context | A **conditional** keyed to an observable predicate |
| Long multi-step task with context drift | **Phase gates** + verification checklist at each transition; offload heavy reference docs |
| Fragile fixed sequence (migrations, releases) | A **low-freedom script** the agent just runs |
| Judgement call / creative work | **High-freedom prose** that explains the *why* |

Avoid: soft "consider/prefer" language for things that are actually mandatory; narrative
"how I solved it once" storytelling; multi-language example dilution; generic section labels.

---

## 5. Workspace trigger auditing

In multi-skill workspaces or plugins, skills can cannibalize each other's triggers if descriptions share too much keyword vocabulary.

Run workspace validation to verify all skills and detect potential trigger collisions:

```bash
python scripts/validate_skill.py --audit-workspace <path/to/workspace> [--strict] [--fail-on-collision]
```

The workspace auditor scans all `SKILL.md` files, verifies name uniqueness, and computes pairwise Jaccard similarity across trigger clauses. Pairs exceeding similarity threshold (Jaccard similarity >= 0.35) with 3+ shared distinctive keywords are flagged as advisory warnings. Pass `--fail-on-collision` if your CI pipeline requires zero trigger overlap.
