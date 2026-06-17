# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Validate an Agent Skill against the agentskills.io spec + house best practices.

Non-interactive by design (safe for agents): reads only, never writes.
DATA  -> stdout as JSON  (the verdict the agent parses)
LOGS  -> stderr          (human-readable progress, never pollutes stdout)
EXIT  0 = pass (no errors)   1 = errors found   2 = bad invocation

Usage:
    python validate_skill.py <path/to/skill-dir>
    python validate_skill.py <path/to/skill-dir> --strict   # warnings fail too
"""
import sys, os, re, json

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED = ("anthropic", "claude")
MAX_NAME, MAX_DESC, MAX_LINES = 64, 1024, 500


def log(msg):
    print(msg, file=sys.stderr)


def parse_frontmatter(text):
    """Minimal, dependency-free YAML frontmatter reader for name/description."""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    block = text[3:end].strip("\n")
    body = text[end + 4:]
    fm, key = {}, None
    for raw in block.splitlines():
        if re.match(r"^[A-Za-z0-9_-]+\s*:", raw):
            key, _, val = raw.partition(":")
            key = key.strip()
            fm[key] = val.strip().strip('"').strip("'")
        elif key and raw.strip():                      # folded multi-line value
            fm[key] = (fm.get(key, "") + " " + raw.strip()).strip()
    return fm, body


def validate(skill_dir):
    errors, warnings = [], []
    name_on_disk = os.path.basename(os.path.normpath(skill_dir))
    md_path = os.path.join(skill_dir, "SKILL.md")

    if not os.path.isfile(md_path):
        errors.append("SKILL.md not found (it is mandatory and case-sensitive)")
        return errors, warnings, {}

    with open(md_path, encoding="utf-8") as fh:
        text = fh.read()
    fm, body = parse_frontmatter(text)

    if fm is None:
        errors.append("No YAML frontmatter found (must start on line 1 between --- markers)")
        return errors, warnings, {}

    # ---- name ----
    name = fm.get("name")
    if not name:
        errors.append("frontmatter: 'name' is required")
    else:
        if not NAME_RE.match(name):
            errors.append(f"name '{name}': must be lowercase a-z 0-9 and single hyphens only")
        if len(name) > MAX_NAME:
            errors.append(f"name '{name}': exceeds {MAX_NAME} chars")
        if any(w in name.lower() for w in RESERVED):
            errors.append(f"name '{name}': must not contain reserved words {RESERVED}")
        if name != name_on_disk:
            errors.append(f"name '{name}' must match the folder name '{name_on_disk}'")

    # ---- description ----
    desc = fm.get("description")
    if not desc:
        errors.append("frontmatter: 'description' is required and must be non-empty")
    else:
        if len(desc) > MAX_DESC:
            errors.append(f"description: {len(desc)} chars exceeds {MAX_DESC}")
        if "<" in desc and ">" in desc:
            errors.append("description: must not contain XML/HTML tags")
        low = desc.lower()
        if low.startswith(("i ", "i'", "we ", "you ", "this skill")):
            warnings.append("description: prefer third person (e.g. 'Generates…', 'Extracts…') over I/we/you/'this skill'")
        if not re.search(r"\b(use when|use this|when the|when a|when you|for )\b", low):
            warnings.append("description: state WHEN to use the skill (triggers), not only what it does")
        if len(desc) < 40:
            warnings.append("description: very short — add concrete trigger keywords a user would actually type")

    # ---- body size (progressive disclosure) ----
    nlines = body.count("\n") + 1
    if nlines > MAX_LINES:
        warnings.append(f"SKILL.md body is {nlines} lines (> {MAX_LINES}): move detail into references/ and link to it")

    # ---- bundled dirs ----
    present = [d for d in ("scripts", "references", "assets") if os.path.isdir(os.path.join(skill_dir, d))]

    facts = {"name": name, "description_chars": len(desc) if desc else 0,
             "body_lines": nlines, "bundled_dirs": present}
    return errors, warnings, facts


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    strict = "--strict" in argv
    if len(args) != 1:
        log("usage: validate_skill.py <path/to/skill-dir> [--strict]")
        return 2
    skill_dir = args[0]
    if not os.path.isdir(skill_dir):
        log(f"error: not a directory: {skill_dir}")
        return 2

    log(f"validating {skill_dir} …")
    errors, warnings, facts = validate(skill_dir)
    for e in errors:
        log(f"  ERROR   {e}")
    for w in warnings:
        log(f"  warning {w}")

    ok = not errors and (not strict or not warnings)
    verdict = {"ok": ok, "errors": errors, "warnings": warnings, "facts": facts}
    print(json.dumps(verdict, indent=2))   # the parseable result -> stdout
    log("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
