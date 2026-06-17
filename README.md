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

This repo **is** an Antigravity plugin: a `plugin.json` marker at the root, with the two skills under
`skills/<name>/SKILL.md`. Install it as a plugin, or copy the loose skills.

### Option A — install as a plugin (recommended)

Antigravity loads plugins from its plugins directory. Clone this repo into it as a named plugin:

```bash
git clone https://github.com/npintaux/meta-skills.git \
  ~/.gemini/antigravity-cli/plugins/meta-skills
```

Then reload (or restart Antigravity) and confirm the skills are present:

```
/skills reload
/skills list      # confirm skill-creator and skill-evaluator appear
```

Both bundled skills (`skill-creator` and `skill-evaluator`) load at once.

### Option B — manual copy of the loose skills

If you just want the skills without the plugin wrapper, copy the two folders out of `skills/` into
a skills directory:

```bash
git clone https://github.com/npintaux/meta-skills.git

# Workspace-scoped (only this project):
mkdir -p .agents/skills
cp -r meta-skills/skills/skill-creator meta-skills/skills/skill-evaluator .agents/skills/

# — or — user-global (every project):
mkdir -p ~/.agents/skills
cp -r meta-skills/skills/skill-creator meta-skills/skills/skill-evaluator ~/.agents/skills/
```

> Antigravity / Gemini CLI accept either `.agents/skills/` (current) or `.gemini/skills/` as the
> workspace path, and `~/.agents/skills/` (or `~/.gemini/skills/`) as the global path.

> **Verify against your version of the docs.** The `plugin.json` fields, the plugins directory path,
> and the exact reload/install commands are evolving across the Gemini CLI → Antigravity CLI
> transition — confirm the structure here against <https://antigravity.google/docs/plugins> before
> publishing.

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
- *"Grade this draft skill file at ./drafts/my-new-skill.md"* → also triggers `skill-evaluator`

The bundled scripts are non-interactive and can also be run directly. Both the `skill-evaluator` skill and the `score_skill.py` script accept either a directory path or a direct path to a standalone `.md` file (useful for early drafting or prototyping before establishing a full directory structure):

```bash
# Structural + best-practice validation (data → stdout, logs → stderr)
python skills/skill-creator/scripts/validate_skill.py path/to/some-skill --strict

# Rubric score with an A–F grade and ranked fixes
python skills/skill-evaluator/scripts/score_skill.py path/to/some-skill-dir-or-file.md --min 0.8
```

## Repository structure

```
meta-skills/                          # the Antigravity plugin
├── plugin.json                       # required plugin marker (name, version, …)
└── skills/                           # skills MUST live here for plugin discovery
    ├── skill-creator/
    │   ├── SKILL.md
    │   ├── references/description-and-eval-cookbook.md   # description patterns + eval method
    │   └── scripts/validate_skill.py                     # non-interactive validator
    └── skill-evaluator/
        ├── SKILL.md
        ├── references/rubric.md                           # the 6-dimension rubric + dynamic checks
        └── scripts/score_skill.py                         # non-interactive rubric scorer
```

> An Antigravity plugin may also carry optional `mcp_config.json`, `hooks.json`, and `rules/` —
> this plugin ships skills only.

## Requirements

- Any `agentskills.io`-compatible agent (Antigravity, Gemini CLI, Claude Code, Codex).
- Python 3.9+ to run the helper scripts (no third-party dependencies).
