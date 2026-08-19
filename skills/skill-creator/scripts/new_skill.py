# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Scaffold a complete, spec-compliant Agent Skill skeleton.

Generates the folder + a SKILL.md whose required sections are present *by
construction* — When to Use, Core Process, Red Flags, and a Verification
checklist (the skill's output acceptance criteria) — plus an evals/ set to fill
in. The agent then replaces the TODO placeholders with real content. This keeps
the creator and the evaluator aligned: what gets generated is what gets graded.

Non-interactive by design (safe for agents): refuses to clobber unless --force.
DATA  -> stdout as JSON  (the paths written)
LOGS  -> stderr          (human-readable progress)
EXIT  0 = written   1 = target exists (use --force)   2 = bad invocation

Usage:
    python new_skill.py <skill-name>
    python new_skill.py <skill-name> --dir path/to/parent   # default: cwd
    python new_skill.py <skill-name> --force                 # overwrite SKILL.md
"""
import sys, os, re, json

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED = ("anthropic", "claude")


def log(msg):
    print(msg, file=sys.stderr)


def skill_md(name):
    # The placeholder description already carries a "Use when" clause so a fresh
    # skeleton fails validation ONLY on the eval placeholders (forcing real work),
    # not on spurious structure errors.
    return f"""---
name: {name}
description: TODO one line on what it does. Use when TODO name the file types, verbs, and phrases a user would actually type to trigger it.
---

# {name.replace('-', ' ').title()}

## Overview
TODO one paragraph: what this skill enables and the mistake it prevents.

## When to Use
Use when the user wants to TODO the concrete situations that should trigger it.

Do **not** use for: TODO the near-misses that should NOT trigger it.

## Core Process

### 1. TODO first step
TODO a concrete, actionable instruction (verb first), not "verify it works".

### 2. TODO second step
TODO ...

## Red Flags
Stop and rework if you notice:
- TODO a corner an agent would cut here;
- hardcoded absolute paths (use paths relative to the skill dir, e.g. `scripts/x.py`);
- scripts missing PEP 723 inline dependency metadata (`# /// script ... # ///`).

## Verification
Ship only when every box is checked (evidence, not assumptions):
- [ ] TODO an objective, checkable output acceptance criterion
- [ ] TODO another one
- [ ] `python scripts/validate_skill.py <dir> --strict` exits 0
"""


def evals_json(name):
    return {
        "skill": name,
        "_help": (
            "Replace every query below with realistic phrasings across all 4 quadrants. "
            "Aim for 16-20 total (8-10 'trigger' and 8-10 'no-trigger'). "
            "Q1 = direct trigger, Q2 = colloquial trigger, Q3 = keyword near-miss, Q4 = sibling skill/adjacent task. "
            "Keep a 60/40 train/validation split. See references/description-and-eval-cookbook.md sec 2."
        ),
        "queries": [
            {
                "quadrant": "Q1_direct",
                "query": "TODO: [Q1 Direct] canonical phrasing directly requesting this skill",
                "expect": "trigger",
                "split": "train"
            },
            {
                "quadrant": "Q1_direct",
                "query": "TODO: [Q1 Direct] another direct phrasing for held-out validation",
                "expect": "trigger",
                "split": "val"
            },
            {
                "quadrant": "Q2_colloquial",
                "query": "TODO: [Q2 Colloquial] indirect / conversational phrasing, different words, same goal",
                "expect": "trigger",
                "split": "train"
            },
            {
                "quadrant": "Q2_colloquial",
                "query": "TODO: [Q2 Colloquial] conversational phrasing for held-out validation",
                "expect": "trigger",
                "split": "val"
            },
            {
                "quadrant": "Q3_near_miss",
                "query": "TODO: [Q3 Near-Miss] shares trigger keywords but has a completely different intent",
                "expect": "no-trigger",
                "note": "why this must NOT fire (intent is different despite keyword overlap)",
                "split": "train"
            },
            {
                "quadrant": "Q4_sibling_adjacent",
                "query": "TODO: [Q4 Sibling/Adjacent] closely related task that belongs to another skill or base agent",
                "expect": "no-trigger",
                "note": "why this must NOT fire (handled by sibling skill or base agent)",
                "split": "val"
            }
        ]
    }


def main(argv):
    pos = [a for a in argv[1:] if not a.startswith("-")]
    force = "--force" in argv
    parent = os.getcwd()
    if "--dir" in argv:
        i = argv.index("--dir")
        if i + 1 < len(argv):
            parent = argv[i + 1]
            pos = [a for a in pos if a != parent]
    if len(pos) != 1:
        log("usage: new_skill.py <skill-name> [--dir parent] [--force]")
        return 2
    name = pos[0]
    if not NAME_RE.match(name):
        log(f"error: name '{name}' must be lowercase a-z 0-9 with single hyphens")
        return 2
    if any(w in name.lower() for w in RESERVED):
        log(f"error: name '{name}' must not contain reserved words {RESERVED}")
        return 2
    if not os.path.isdir(parent):
        log(f"error: parent is not a directory: {parent}")
        return 2

    skill_dir = os.path.join(parent, name)
    md_path = os.path.join(skill_dir, "SKILL.md")
    evals_path = os.path.join(skill_dir, "evals", "trigger_evals.json")

    if os.path.exists(md_path) and not force:
        log(f"error: {md_path} already exists (pass --force to overwrite)")
        print(json.dumps({"ok": False, "path": md_path, "reason": "exists"}, indent=2))
        return 1

    os.makedirs(os.path.join(skill_dir, "evals"), exist_ok=True)
    os.makedirs(os.path.join(skill_dir, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(skill_dir, "references"), exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(skill_md(name))
    if not os.path.exists(evals_path) or force:
        with open(evals_path, "w", encoding="utf-8") as fh:
            json.dump(evals_json(name), fh, indent=2)
            fh.write("\n")

    log(f"scaffolded {skill_dir} — now fill the TODOs in SKILL.md and evals/trigger_evals.json")
    print(json.dumps({"ok": True, "skill_dir": skill_dir,
                      "wrote": [md_path, evals_path]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
