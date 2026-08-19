---
name: skill-creator
description: Creates, audits, and improves Agent Skills (SKILL.md) for Antigravity, Gemini CLI, and any agentskills.io-compatible agent. Use when the user wants to author a new skill, scaffold a SKILL.md, fix a skill that never triggers, review or harden an existing skill, or turn a repetitive workflow into a reusable skill.
---

# Skill Creator

## Overview
This skill turns a repetitive task into a **correct, well-triggering, lean** Agent Skill — not just a
syntactically valid folder. A scaffolder gives you the right files; this gives you a skill that
actually fires at the right moment, changes the agent's behaviour, and stays small enough to not
rot the context window. Follow the process: a good skill is *measured*, not guessed.

## When to Use
Use when the user asks to:
- create a new skill / "make a skill for X" / scaffold a `SKILL.md`;
- fix a skill that doesn't trigger or triggers on the wrong requests;
- review, audit, shorten, or harden an existing skill;
- package an existing repetitive workflow into something reusable.

Do **not** use for: writing ordinary application code, authoring a one-off prompt, or editing
`AGENTS.md` / repo memory files (those are always-on guidance, not skills).

## Core Process

### 1. Capture intent (interview before authoring)
Before writing anything, establish four things — mine the current conversation first, then ask only
what's still missing:
1. **What** should the skill enable? (one concrete capability — keep it single-responsibility)
2. **When** should it trigger? Collect the *actual phrases and contexts* a user would use.
3. **Output**: what does success look like? (format, files, exit criteria)
4. **Evals?** If the output is objectively checkable → plan evals (step 6). If purely subjective → optional.
Also note dependencies, example inputs, and edge cases. Research unknowns in parallel if you can.

### 2. Choose the body shape (match the form to the failure)
Decide *how the task tends to fail* and pick the matching structure — see
`references/description-and-eval-cookbook.md` §4. Discipline failures need a rationalizations
table + red flags; wrong-shaped output needs a positive recipe; fragile sequences need a script.
Do not default everything to prose.

### 3. Scaffold the folder
Generate a spec-compliant skeleton — the required sections come pre-wired so you never forget them:
```
python scripts/new_skill.py your-skill-name --dir path/to/parent
```
This writes the tree below with a `SKILL.md` that already has `## When to Use` + `## Verification`
(the acceptance criteria) and an `evals/` set, all as TODOs to fill in the next steps.
```
your-skill-name/
├── SKILL.md          # required — frontmatter + lean body
├── scripts/          # optional — deterministic, non-interactive helpers
├── references/       # optional — deep docs, loaded on demand
├── evals/            # recommended — trigger_evals.json, the committed eval set
└── assets/           # optional — templates / files the skill emits
```
The folder name **must** equal the frontmatter `name`.

### 4. Write the frontmatter (the load-bearing step)
Two fields are required (`name`, `description`); optional engine fields (`allowed-tools`, `disable-model-invocation`, `compatibility`) are supported when needed:
- **`name`** — lowercase letters/numbers/hyphens, ≤ 64 chars, matches the folder, and must **not**
  contain the words `anthropic` or `claude`.
- **`description`** — third person, ≤ 1024 chars, no XML tags, and carries **both what it does AND
  when to use it**. This single field decides whether the skill ever fires.
  Lead with concrete trigger keywords; be assertive; do not just restate the body's steps.
  See `references/description-and-eval-cookbook.md` §1 for good/bad examples.

### 5. Write the body (lean + concrete)
- Keep `SKILL.md` **under 500 lines**. Push deep material into `references/` and link by name.
- Use numbered, **actionable** steps — `Run the test suite and inspect the output`, not
  `Verify the system works`. Show templates/output as literal blocks (models pattern-match structure).
- Give **one default path** ("defaults, not menus"); mention alternatives only as a fallback.
- Explain the *why* for judgement calls; reserve rigid commands for genuinely fragile steps.
- **Always include a `## When to Use` and a `## Verification` section.** Verification is the skill's
  **acceptance criteria**: an objective, checkable exit list (`row count matches`, `output is valid
  JSON`), not a hand-wavy "it works". The validator and the evaluator both require these.
- **Reference bundled scripts by a path relative to the skill** (`scripts/x.py`), never an absolute
  one — the home dir varies by login and OS (`/home/…`, `/Users/…`, `C:\Users\…`) and the install dir
  varies by vendor (`.claude/` vs `.agents/` vs `.gemini/`). Inside a script, resolve its own location
  at runtime (`Path(__file__).resolve().parent`); for a real home dir use `os.path.expanduser("~")`,
  never a literal login name.

### 6. Build a trigger-evaluation set (and commit it)
Scaffold the eval file, then fill it with real queries — a committed eval set is what makes a skill
*measured* rather than guessed, and it's what the validator checks in step 8:
```
python scripts/new_evals.py path/to/your-skill        # writes evals/trigger_evals.json
```
Replace the TODO placeholders with ~16–20 realistic queries covering the **4 quadrants** (8–10 per side):
Q1 (direct triggers), Q2 (colloquial triggers), Q3 (keyword near-misses that must not fire),
and Q4 (sibling/adjacent tasks). Keep a train/validation split so you don't overfit the description to one
phrasing. Then run each query 3× in fresh sessions — target should-trigger > 50% activation,
near-miss < 50%. Full method + file schema: `references/description-and-eval-cookbook.md` §2.

### 7. Test behaviour vs. baseline
Run 2–3 realistic prompts **without** the skill (baseline) and **with** it. The skill earns its place
only if it changes behaviour — quality, step count, or token use. Grade on objective assertions where
possible. If with-skill ≈ baseline, cut or sharpen it. (See §3 of the cookbook.) "No skill without a
failing test first."

### 8. Validate, then package
Run the bundled validator before shipping:
```
python scripts/validate_skill.py path/to/your-skill --strict
# Or audit an entire multi-skill workspace for trigger collisions:
python scripts/validate_skill.py --audit-workspace path/to/workspace [--strict] [--fail-on-collision]
```
It checks the frontmatter rules, reserved words, description quality, body size, **and that a real
`evals/trigger_evals.json` exists with at least one should-NOT-trigger case** — it prints a JSON
verdict (data → stdout, logs → stderr, non-zero exit on failure). Fix every ERROR; resolve warnings.
Under `--strict` a missing eval set is itself an error: a skill you never tested doesn't ship.

### 9. Install for Antigravity / Gemini CLI
Drop the folder into a skills directory and reload:
- **Antigravity / Gemini CLI (workspace)**: `.agents/skills/your-skill-name/` (alias `.gemini/skills/`)
- **User-global**: `~/.agents/skills/` (alias `~/.gemini/skills/`)
- Or install from git: `gemini skills install <git-url>` (Antigravity CLI: same verb).
- The same folder also works in Claude Code (`.claude/skills/`), the Claude API, and OpenAI Codex —
  it's the open agentskills.io standard. Author once, run across vendors.

## Common Rationalizations
| The excuse | The reality |
|---|---|
| "The description is obvious, I'll keep it short." | A vague description is the #1 reason skills never fire. Spend real effort here. |
| "It's valid YAML, so it's done." | Valid ≠ good. Syntactically correct skills that never trigger or don't change behaviour are worthless. |
| "I'll skip the eval, I tested it once." | One happy-path shot hides false-negatives and false-positives. Use the labelled query set. |
| "I'll put everything in SKILL.md so it's all in one place." | That bloats context and causes 'context rot'. Push detail into `references/`. |
| "I'll list a few options so the agent can choose." | Menus make the agent dither and burn tokens. Give one default. |
| "The script asks for confirmation to be safe." | Interactive prompts hang the agent forever. Use `--dry-run` + an explicit `--force` flag instead. |

## Red Flags
Stop and rework if you notice:
- the `description` summarizes the workflow instead of stating *when* to use the skill;
- `SKILL.md` is creeping past 500 lines, or reference detail is inlined in the body;
- there are no should-NOT-trigger test cases (you've only proven it *can* fire, not that it won't over-fire);
- the skill changes nothing versus baseline;
- a bundled script prompts interactively, prints logs to stdout, or has no error message on failure;
- there is no `## Verification` section — the skill has no acceptance criteria to ship against;
- a bundled file is referenced by an absolute path (`…/scripts/…`, any home dir or drive) instead of relative;
- the `name` doesn't match the folder, or contains `anthropic`/`claude`.

## Verification
Ship only when every box is checked (evidence, not assumptions):
- [ ] Folder name equals the frontmatter `name` (kebab-case, ≤ 64 chars, no reserved words)
- [ ] `description` is third person and states **what + when**, with real trigger keywords
- [ ] `SKILL.md` body is under 500 lines; deep material lives in `references/`
- [ ] Steps are concrete and actionable; one default path, not a menu
- [ ] Bundled scripts are non-interactive, declare deps inline, and route data→stdout / logs→stderr
- [ ] `evals/trigger_evals.json` is committed, with real should-trigger **and** should-NOT-trigger queries
- [ ] Trigger eval run: should-trigger > 50%, should-NOT-trigger < 50% on a held-out set
- [ ] Behaviour differs from baseline on at least one realistic prompt
- [ ] `python scripts/validate_skill.py <dir> --strict` exits 0

## Reference files
- `references/description-and-eval-cookbook.md` — description patterns, the trigger-eval method
  (train/val split), the `trigger_evals.json` schema, baseline testing, and the form-to-failure
  table. Read it at steps 4, 6, and 7.
- `scripts/new_skill.py` — scaffolds a full spec-compliant skill skeleton (SKILL.md + required sections + evals/).
- `scripts/new_evals.py` — scaffolds just `evals/trigger_evals.json` (non-interactive; `--force` to overwrite).
- `scripts/validate_skill.py` — non-interactive structural + best-practice validator (incl. the eval-set gate).
