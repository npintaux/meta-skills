# meta-skills

Two portable **Agent Skills** that help you author and review *other* Agent Skills — the
[`agentskills.io`](https://agentskills.io) `SKILL.md` standard used by Antigravity, Gemini CLI,
Claude Code, the Claude API, and OpenAI Codex.

| Skill | What it does |
|-------|--------------|
| **`skill-creator`** | Turns a repetitive workflow into a *correct, well-triggering, lean* skill — not just a valid folder. Walks you through interview → a proper what-plus-when description → progressive disclosure → an eval/trigger loop → validation before shipping. |
| **`skill-evaluator`** | Grades an existing skill. Runs a 6-dimension static rubric (frontmatter, description trigger quality, progressive disclosure, body concreteness, structure, script hygiene) for an A–F score, then drives the dynamic checks a script can't do: does it actually trigger, and does it change the agent's behaviour versus no skill? |

## Why these exist

Most "skill creator" tooling is a **scaffolder**: it
generates the folder and frontmatter *syntax*, but not a *good* skill — the quality guidance lives in
a separate docs page the tool doesn't enforce. Antigravity ships no skill-authoring meta-skill at all.
These two close that gap by baking the authoring best practices into the skills themselves.

Both are self-contained, dependency-free, and portable. They also dogfood each other: run through one
another, each scores an **A**.

## Install in Antigravity

A skill is just a folder containing a `SKILL.md`. Antigravity discovers skills from a `skills`
directory; put these two folders there and reload.

### Option A — install from this repo (recommended)

```bash
agy skills install https://github.com/npintaux/meta-skills.git
```

This pulls the repository and registers every skill folder it finds (`skill-creator` and
`skill-evaluator`).

### Option B — manual copy

Clone the repo and copy the two skill folders into a skills directory:

```bash
git clone https://github.com/npintaux/meta-skills.git

# Workspace-scoped (only this project):
mkdir -p .agents/skills
cp -r meta-skills/skill-creator meta-skills/skill-evaluator .agents/skills/

# — or — user-global (every project):
mkdir -p ~/.agents/skills
cp -r meta-skills/skill-creator meta-skills/skill-evaluator ~/.agents/skills/
```

> Antigravity / Gemini CLI accept either `.agents/skills/` (current) or `.gemini/skills/` as the
> workspace path, and `~/.agents/skills/` (or `~/.gemini/skills/`) as the global path.

### Reload and verify

In an Antigravity / Gemini CLI session:

```
/skills reload
/skills list      # confirm skill-creator and skill-evaluator appear
```

Skills are **model-invoked**: just describe your task ("turn this workflow into a skill", "review
this skill and tell me what to fix") and the agent loads the matching skill automatically based on
its `description`.

### Works elsewhere too

The same folders are valid `agentskills.io` skills, so they also drop into:

- **Claude Code** — `.claude/skills/` (project) or `~/.claude/skills/` (personal)
- **OpenAI Codex** — `.agents/skills/`

## Usage

Once installed, just ask the agent in natural language:

- *"Create a skill that scaffolds a new microservice from our template."* → triggers `skill-creator`
- *"Review the skill in ./my-skill and tell me whether it's ready to ship."* → triggers `skill-evaluator`

The bundled scripts are non-interactive and can also be run directly:

```bash
# Structural + best-practice validation (data → stdout, logs → stderr)
python skill-creator/scripts/validate_skill.py path/to/some-skill --strict

# Rubric score with an A–F grade and ranked fixes
python skill-evaluator/scripts/score_skill.py path/to/some-skill --min 0.8
```

## Repository structure

```
meta-skills/
├── skill-creator/
│   ├── SKILL.md
│   ├── references/description-and-eval-cookbook.md   # description patterns + eval method
│   └── scripts/validate_skill.py                     # non-interactive validator
└── skill-evaluator/
    ├── SKILL.md
    ├── references/rubric.md                           # the 6-dimension rubric + dynamic checks
    └── scripts/score_skill.py                         # non-interactive rubric scorer
```

## Requirements

- Any `agentskills.io`-compatible agent (Antigravity, Gemini CLI, Claude Code, Codex).
- Python 3.9+ to run the helper scripts (no third-party dependencies).
