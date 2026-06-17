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
```
your-skill-name/
├── SKILL.md          # required — frontmatter + lean body
├── scripts/          # optional — deterministic, non-interactive helpers
├── references/       # optional — deep docs, loaded on demand
└── assets/           # optional — templates / files the skill emits
```
The folder name **must** equal the frontmatter `name`.

### 4. Write the frontmatter (the load-bearing step)
Two required fields, nothing else needed:
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

### 6. Build a trigger-evaluation set
Generate ~15–20 realistic queries split into **should-trigger** and **should-NOT-trigger** (near-misses
with overlapping keywords but different goals). Keep a train/validation split so you don't overfit the
description to one phrasing. Target: should-trigger > 50% activation, near-miss < 50%, over 3 runs each.
Full method: `references/description-and-eval-cookbook.md` §2.

### 7. Test behaviour vs. baseline
Run 2–3 realistic prompts **without** the skill (baseline) and **with** it. The skill earns its place
only if it changes behaviour — quality, step count, or token use. Grade on objective assertions where
possible. If with-skill ≈ baseline, cut or sharpen it. (See §3 of the cookbook.) "No skill without a
failing test first."

### 8. Validate, then package
Run the bundled validator before shipping:
```
python scripts/validate_skill.py path/to/your-skill --strict
```
It checks the frontmatter rules, reserved words, description quality, and body size, and prints a JSON
verdict (data → stdout, logs → stderr, non-zero exit on failure). Fix every ERROR; resolve warnings.

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
- the `name` doesn't match the folder, or contains `anthropic`/`claude`.

## Verification
Ship only when every box is checked (evidence, not assumptions):
- [ ] Folder name equals the frontmatter `name` (kebab-case, ≤ 64 chars, no reserved words)
- [ ] `description` is third person and states **what + when**, with real trigger keywords
- [ ] `SKILL.md` body is under 500 lines; deep material lives in `references/`
- [ ] Steps are concrete and actionable; one default path, not a menu
- [ ] Bundled scripts are non-interactive, declare deps inline, and route data→stdout / logs→stderr
- [ ] Trigger eval run: should-trigger > 50%, should-NOT-trigger < 50% on a held-out set
- [ ] Behaviour differs from baseline on at least one realistic prompt
- [ ] `python scripts/validate_skill.py <dir> --strict` exits 0

## Reference files
- `references/description-and-eval-cookbook.md` — description patterns, the trigger-eval method
  (train/val split), baseline testing, and the form-to-failure table. Read it at steps 4, 6, and 7.
- `scripts/validate_skill.py` — non-interactive structural + best-practice validator.
