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
    python validate_skill.py <path/to/skill-dir> [--strict]
    python validate_skill.py --audit-workspace <path/to/workspace> [--strict]
"""
import sys, os, re, json

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED = ("anthropic", "claude")
MAX_NAME, MAX_DESC, MAX_LINES = 64, 1024, 500

# Matches genuine absolute filesystem paths (POSIX root, Windows C:\, or UNC \\)
# that reach into bundled directories (scripts/, references/, assets/).
# Correctly ignores relative paths like `skills/my-skill/scripts/x.py` or `scripts/x.py`.
ABS_BUNDLED_RE = re.compile(
    r"""(?:\b[A-Za-z]:[\\/]|\\\\[^\s"'`)]+[\\/]|(?:^|(?<=[^\w/:~]))/[^\s"'`)]*)[^\s"'`)]*[\\/](?:scripts|references|assets)[\\/]"""
)

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by",
    "from", "is", "are", "was", "were", "be", "been", "this", "that", "it", "its", "as",
    "when", "use", "user", "wants", "asks", "needs", "using", "into", "can", "you", "your",
    "we", "our", "all", "any", "how", "what", "which", "who", "whom", "will", "would", "should"
}


def log(msg):
    print(msg, file=sys.stderr)


def parse_frontmatter(text):
    """Minimal, dependency-free YAML frontmatter reader supporting strings, booleans, and lists."""
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
            val = val.strip()
            if val.lower() == "true":
                fm[key] = True
            elif val.lower() == "false":
                fm[key] = False
            elif val.startswith("[") and val.endswith("]"):
                items = [x.strip().strip('"').strip("'") for x in val[1:-1].split(",") if x.strip()]
                fm[key] = items
            else:
                fm[key] = val.strip('"').strip("'")
        elif key and raw.strip():                      # folded multi-line value
            if isinstance(fm.get(key), str):
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
        if not isinstance(name, str) or not NAME_RE.match(name):
            errors.append(f"name '{name}': must be lowercase a-z 0-9 and single hyphens only")
        if isinstance(name, str) and len(name) > MAX_NAME:
            errors.append(f"name '{name}': exceeds {MAX_NAME} chars")
        if isinstance(name, str):
            segments = set(name.lower().split("-"))
            if any(w in segments for w in RESERVED):
                errors.append(f"name '{name}': must not contain reserved words {RESERVED}")
        if name != name_on_disk:
            errors.append(f"name '{name}' must match the folder name '{name_on_disk}'")

    # ---- description ----
    desc = fm.get("description")
    if not desc:
        errors.append("frontmatter: 'description' is required and must be non-empty")
    else:
        if not isinstance(desc, str):
            errors.append("description: must be a text string")
            desc = str(desc)
        if len(desc) > MAX_DESC:
            errors.append(f"description: {len(desc)} chars exceeds {MAX_DESC}")
        if re.search(r"</?[A-Za-z][^>]*>", desc):
            errors.append("description: must not contain XML/HTML tags")
        low = desc.lower()
        if low.startswith(("i ", "i'", "we ", "you ", "this skill")):
            warnings.append("description: prefer third person (e.g. 'Generates…', 'Extracts…') over I/we/you/'this skill'")
        # A description with no WHEN/trigger is the #1 reason skills never fire — warn author with broadened phrases.
        if not re.search(r"\b(use when|use this|when |for |run with|invoke |trigger|reach for|handy for|designed to|designed for|ideal for|helps with|helps to|handles)\b", low):
            warnings.append("description: state WHEN to use the skill (e.g. 'Use when…', 'Reach for…') to help agent discovery")
        if len(desc) < 40:
            warnings.append("description: very short — add concrete trigger keywords a user would actually type")

    # ---- optional frontmatter fields (tolerant validation) ----
    if "disable-model-invocation" in fm:
        dmi = fm["disable-model-invocation"]
        if not isinstance(dmi, bool) and str(dmi).lower() not in ("true", "false"):
            warnings.append("disable-model-invocation: expected boolean (true/false)")

    if "allowed-tools" in fm and not isinstance(fm["allowed-tools"], (str, list)):
        warnings.append("allowed-tools: expected comma-separated string or list of tool names")
    if "tools" in fm and not isinstance(fm["tools"], (str, list)):
        warnings.append("tools: expected comma-separated string or list of tool names")

    # ---- body size (progressive disclosure) ----
    nlines = body.count("\n") + 1
    if nlines > MAX_LINES:
        errors.append(f"SKILL.md body is {nlines} lines (> {MAX_LINES}): move detail into references/ and link to it")

    # ---- structure: the skill's acceptance criteria (aligned with score_skill.py) ----
    if not re.search(r"(?im)^#+\s*when to use", body):
        warnings.append("no '## When to Use' section — state triggers + exclusions in the body, not only the description")
    if not (re.search(r"(?im)^#+\s*verification", body) or re.search(r"- \[ \]", body)):
        warnings.append("no Verification checklist — add the output acceptance criteria as an evidence-based '- [ ]' list")

    # ---- portability: absolute path check ----
    if re.search(ABS_BUNDLED_RE, body):
        warnings.append("absolute path to a bundled file (…/scripts|references|assets/…) — reference it relative to the skill dir, e.g. scripts/x.py")

    # ---- trigger evals ----
    n_trigger, n_notrigger, n_real = check_evals(skill_dir, errors, warnings)

    # ---- bundled dirs ----
    present = [d for d in ("scripts", "references", "assets", "evals") if os.path.isdir(os.path.join(skill_dir, d))]

    facts = {
        "name": name,
        "description_chars": len(desc) if desc else 0,
        "body_lines": nlines,
        "bundled_dirs": present,
        "evals": {"trigger": n_trigger, "no_trigger": n_notrigger, "real_queries": n_real}
    }
    return errors, warnings, facts


def check_evals(skill_dir, errors, warnings):
    """Inspect evals/trigger_evals.json. Returns (n_trigger, n_no_trigger, n_real)."""
    path = os.path.join(skill_dir, "evals", "trigger_evals.json")
    if not os.path.isfile(path):
        warnings.append("no evals/trigger_evals.json — scaffold it with scripts/new_evals.py, then fill real queries (required under --strict)")
        return 0, 0, 0
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as e:
        errors.append(f"evals/trigger_evals.json: invalid JSON ({e})")
        return 0, 0, 0
    queries = data.get("queries") if isinstance(data, dict) else data
    if not isinstance(queries, list):
        errors.append('evals/trigger_evals.json: expected a list of queries or {"queries": [...]}')
        return 0, 0, 0
    real = [q for q in queries if isinstance(q, dict)
            and not str(q.get("query", "")).strip().upper().startswith("TODO")]
    n_trigger = sum(1 for q in real if str(q.get("expect", "")).lower() == "trigger")
    n_notrigger = sum(1 for q in real if str(q.get("expect", "")).lower() in ("no-trigger", "no_trigger"))
    if not real:
        errors.append("evals/trigger_evals.json: only TODO placeholders — replace them with real queries")
    else:
        if not n_trigger:
            errors.append("evals: no should-trigger queries (expect: trigger)")
        if not n_notrigger:
            errors.append("evals: no should-NOT-trigger queries (expect: no-trigger) — you've only proven it can fire, not that it won't over-fire")
        if len(real) < 6:
            warnings.append(f"evals: only {len(real)} real queries; aim for ~16-20 (8-10 per side across 4 quadrants)")
    return n_trigger, n_notrigger, len(real)


def extract_trigger_tokens(desc):
    """Extract significant keywords from a skill description for collision analysis."""
    if not desc:
        return set()
    low = desc.lower()
    # Focus on the trigger clause if present
    m = re.search(r"\b(?:use when|when the|when a|when you|for |run with|invoke with|triggered by)\b(.*)", low)
    clause = m.group(1) if m else low
    words = re.findall(r"[a-z0-9_-]+", clause)
    return {w for w in words if len(w) >= 3 and w not in STOPWORDS}


def find_skills_in_workspace(workspace_dir):
    """Return dict mapping path to name if present, or just path."""
    skills = {}
    for root, dirs, files in os.walk(workspace_dir):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "venv", ".venv", "__pycache__")]
        if "SKILL.md" in files:
            skills[root] = root
    return skills


def audit_workspace(workspace_dir, strict=False, fail_on_collision=False):
    """Audits an entire workspace of skills for individual validity and cross-skill trigger collisions."""
    log(f"Workspace audit for {workspace_dir} …")
    skills_map = find_skills_in_workspace(workspace_dir)
    if not skills_map:
        log("No skills found in workspace.")
        return 0

    log(f"Found {len(skills_map)} skill(s).")
    all_errors = []
    all_warnings = []
    skill_warnings = []
    collision_warnings = []
    skills_results = []

    for sdir, rel in sorted(skills_map.items(), key=lambda x: x[1]):
        errs, warns, facts = validate(sdir)
        sname = facts.get("name") or os.path.basename(sdir)
        skills_results.append({
            "name": sname,
            "path": sdir,
            "ok": len(errs) == 0 and (not strict or len(warns) == 0),
            "errors": errs,
            "warnings": warns,
            "facts": facts
        })
        if errs or warns:
            mark = "FAIL" if errs or (strict and warns) else "PASS"
            log(f"  [{mark}] {sname} ({sdir})")
            for e in errs:
                msg = f"{sname}: {e}"
                all_errors.append(msg)
                log(f"    ERROR   {e}")
            for w in warns:
                msg = f"{sname}: {w}"
                all_warnings.append(msg)
                skill_warnings.append(msg)
                log(f"    warning {w}")
        else:
            log(f"  [PASS] {sname} ({sdir})")

    # --- Cross-skill Collision Detection ---
    collisions = []
    log("Checking for cross-skill collisions …")

    # 1. Duplicate name detection (hard error)
    names_seen = {}
    for res in skills_results:
        nm = res["name"]
        if nm in names_seen:
            msg = f"Duplicate skill name '{nm}' in {names_seen[nm]} and {res['path']}"
            all_errors.append(msg)
            log(f"  ERROR   {msg}")
        else:
            names_seen[nm] = res["path"]

    # 2. Trigger Keyword Jaccard Similarity & Overlap (advisory warning)
    skill_tokens = {}
    for sdir, res in skills_map.items():
        md_path = os.path.join(sdir, "SKILL.md")
        if os.path.isfile(md_path):
            with open(md_path, encoding="utf-8") as fh:
                fm, _ = parse_frontmatter(fh.read())
                desc = fm.get("description", "") if fm else ""
                skill_tokens[os.path.basename(sdir)] = extract_trigger_tokens(desc)

    skill_names = list(skill_tokens.keys())
    for i in range(len(skill_names)):
        for j in range(i + 1, len(skill_names)):
            na, nb = skill_names[i], skill_names[j]
            ta, tb = skill_tokens[na], skill_tokens[nb]
            union = ta | tb
            inter = ta & tb
            sim = len(inter) / len(union) if union else 0.0
            shared = sorted(list(inter))

            is_collision = sim >= 0.35 and len(inter) >= 3
            if is_collision:
                msg = f"Potential trigger collision between '{na}' and '{nb}' (Jaccard similarity {sim:.2f}, shared tokens: {shared})"
                all_warnings.append(msg)
                collision_warnings.append(msg)
                log(f"  warning {msg}")

            collisions.append({
                "skill_a": na,
                "skill_b": nb,
                "similarity": round(sim, 3),
                "shared_tokens": shared,
                "collision": is_collision
            })

    # Failure criteria:
    # 1. Any individual skill errors or duplicate name errors -> fail
    # 2. Strict mode with individual skill warnings -> fail
    # 3. Explicit --fail-on-collision with collision warnings -> fail
    ok = (not all_errors) and (not (strict and skill_warnings)) and (not (fail_on_collision and collision_warnings))
    verdict = {
        "ok": ok,
        "workspace": workspace_dir,
        "skills_count": len(skills_results),
        "skills": skills_results,
        "collisions": collisions,
        "errors": all_errors,
        "warnings": all_warnings
    }
    print(json.dumps(verdict, indent=2))
    log(f"WORKSPACE AUDIT {'PASS' if ok else 'FAIL'} ({len(skills_results)} skills checked, {len(all_errors)} errors, {len(all_warnings)} warnings)")
    return 0 if ok else 1


def main(argv):
    strict = "--strict" in argv
    fail_on_collision = "--fail-on-collision" in argv
    clean_args = [a for a in argv[1:] if a not in ("--strict", "--fail-on-collision")]

    if len(clean_args) == 2 and clean_args[0] in ("--audit-workspace", "--audit"):
        ws_dir = clean_args[1]
        if not os.path.isdir(ws_dir):
            log(f"error: not a directory: {ws_dir}")
            return 2
        return audit_workspace(ws_dir, strict=strict, fail_on_collision=fail_on_collision)

    pos = [a for a in clean_args if not a.startswith("-")]
    if len(pos) != 1:
        log("usage:")
        log("    python validate_skill.py <path/to/skill-dir> [--strict]")
        log("    python validate_skill.py --audit-workspace <path/to/workspace> [--strict] [--fail-on-collision]")
        return 2

    skill_dir = pos[0]
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
    print(json.dumps(verdict, indent=2))
    log("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
