# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Scaffold a trigger-evaluation set for an Agent Skill.

Writes `evals/trigger_evals.json` next to the skill's SKILL.md so the eval set
becomes a committed artifact (not a throwaway you build in one session). The
agent then replaces the placeholders with real should-trigger / should-NOT-trigger
queries at step 6 of skill-creator. Running the queries stays agent-driven — a
script cannot spawn the fresh sessions that trigger-testing needs.

Non-interactive by design (safe for agents): refuses to clobber unless --force.
DATA  -> stdout as JSON  (the path written + the template it wrote)
LOGS  -> stderr          (human-readable progress)
EXIT  0 = written   1 = file exists (use --force)   2 = bad invocation

Usage:
    python new_evals.py <path/to/skill-dir>
    python new_evals.py <path/to/skill-dir> --force   # overwrite an existing file
"""
import sys, os, json

FILENAME = "trigger_evals.json"


def log(msg):
    print(msg, file=sys.stderr)


def template(skill_name):
    """A starter eval set: real schema, placeholder content covering the 4 quadrants.
    Keeps at least one should-NOT-trigger case so the file passes the validator's
    'near-miss required' gate only once the agent has done the real work."""
    return {
        "skill": skill_name,
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
    args = [a for a in argv[1:] if not a.startswith("-")]
    force = "--force" in argv
    if len(args) != 1:
        log("usage: new_evals.py <path/to/skill-dir> [--force]")
        return 2
    skill_dir = args[0]
    if not os.path.isdir(skill_dir):
        log(f"error: not a directory: {skill_dir}")
        return 2

    skill_name = os.path.basename(os.path.normpath(skill_dir))
    evals_dir = os.path.join(skill_dir, "evals")
    out_path = os.path.join(evals_dir, FILENAME)

    if os.path.exists(out_path) and not force:
        log(f"error: {out_path} already exists (pass --force to overwrite)")
        print(json.dumps({"ok": False, "path": out_path, "reason": "exists"}, indent=2))
        return 1

    os.makedirs(evals_dir, exist_ok=True)
    data = template(skill_name)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")

    log(f"wrote {out_path} — now replace the TODO placeholders with real queries")
    print(json.dumps({"ok": True, "path": out_path, "template": data}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
