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
    """A starter eval set: real schema, placeholder content the agent must replace.
    Keeps at least one should-NOT-trigger case so the file passes the validator's
    'near-miss required' gate only once the agent has done the real work."""
    return {
        "skill": skill_name,
        "_help": (
            "Replace every query below with realistic phrasings. Aim for 15-20 total, "
            "8-10 'trigger' and 8-10 'no-trigger'. no-trigger = near-misses that share "
            "keywords but have a different goal. Run each 3x in fresh sessions; keep a "
            "60/40 train/validation split. See references/description-and-eval-cookbook.md sec 2."
        ),
        "queries": [
            {"query": "TODO: a colloquial way a user asks for this skill", "expect": "trigger"},
            {"query": "TODO: another phrasing, different words, same goal", "expect": "trigger"},
            {"query": "TODO: a near-miss that shares keywords but wants something else",
             "expect": "no-trigger", "note": "why this must NOT fire"},
        ],
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
