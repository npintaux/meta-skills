# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Static rubric scorer for an Agent Skill. Input: a skill directory or a standalone .md file.

Self-contained (no cross-skill imports), read-only, non-interactive.
DATA  -> stdout as JSON  (per-dimension scores + overall grade + fixes)
LOGS  -> stderr          (human-readable)
EXIT  0 = grade >= pass threshold   1 = below threshold   2 = bad invocation

This covers the STATIC half of evaluation. The dynamic half — trigger-rate and
baseline-vs-with-skill behavioural testing — needs a live agent and is driven by
SKILL.md, not this script.

Usage:
    python score_skill.py <path/to/skill-dir-or-file.md> [--min 0.8]
"""
import sys, os, re, json

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED = ("anthropic", "claude")
VAGUE = ("verify it works", "make sure", "as needed", "appropriately", "etc.",
         "and so on", "handle it", "do the right thing")
MENU = ("alternatively", "you could also", "another option", "or you can", "option a", "option b")
# Actual interactive *call* constructs — matched after string/comment literals are stripped,
# so a script that merely mentions these words (e.g. this scorer) is not flagged.
INTERACTIVE = (r"\binput\s*\(", r"\braw_input\s*\(", r"\bread\s+-r?p\b", r"\bread\s+-p\b")


# Matches genuine absolute filesystem paths (POSIX root, Windows C:\, or UNC \\)
# that reach into bundled directories (scripts/, references/, assets/).
ABS_BUNDLED_RE = re.compile(
    r"""(?:\b[A-Za-z]:[\\/]|\\\\[^\s"'`)]+[\\/]|(?:^|(?<=[^\w/:~]))/[^\s"'`)]*)[^\s"'`)]*[\\/](?:scripts|references|assets)[\\/]"""
)


def strip_literals(src):
    """Remove triple/single/double-quoted strings and # comments so pattern matching
    keys on code, not on string constants. Good enough for hygiene heuristics."""
    src = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', " ", src)
    src = re.sub(r'"[^"\n]*"|\'[^\'\n]*\'', " ", src)
    src = re.sub(r"#[^\n]*", " ", src)
    return src


def log(m): print(m, file=sys.stderr)


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    block, body = text[3:end].strip("\n"), text[end + 4:]
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
        elif key and raw.strip():
            if isinstance(fm.get(key), str):
                fm[key] = (fm.get(key, "") + " " + raw.strip()).strip()
    return fm, body


def dim(name, score, mx, notes, fixes):
    return {"dimension": name, "score": score, "max": mx,
            "notes": notes, "fixes": fixes}


def score(target_path):
    dims = []
    if os.path.isfile(target_path):
        md = target_path
        skill_dir = os.path.dirname(os.path.abspath(target_path))
        if os.path.basename(md).lower() == "skill.md":
            name_disk = os.path.basename(os.path.normpath(skill_dir))
        else:
            name_disk = os.path.splitext(os.path.basename(md))[0]
    else:
        skill_dir = target_path
        name_disk = os.path.basename(os.path.normpath(skill_dir))
        md = os.path.join(skill_dir, "SKILL.md")

    if not os.path.isfile(md):
        return [dim("structure", 0, 2, [f"{os.path.basename(md)} missing"], [f"Add a {os.path.basename(md)} file"])], {}
    text = open(md, encoding="utf-8").read()
    fm, body = parse_frontmatter(text)
    fm = fm or {}
    name, desc = fm.get("name", ""), fm.get("description", "")
    body_lc = body.lower()

    # 1. Frontmatter validity (hard, max 2)
    n, notes, fixes = 2, [], []
    if not name: n = 0; notes.append("name missing"); fixes.append("Add 'name'")
    else:
        if not NAME_RE.match(name): n = 0; notes.append(f"name '{name}' not kebab-case"); fixes.append("Use lowercase + single hyphens")
        if len(name) > 64: n = min(n, 1); notes.append("name > 64 chars")
        segments = set(name.lower().split("-"))
        if any(w in segments for w in RESERVED): n = 0; notes.append("name uses reserved word"); fixes.append("Remove anthropic/claude from name")
        if name != name_disk: n = min(n, 1); notes.append(f"name != folder '{name_disk}'"); fixes.append("Make name match folder")
    if not desc: n = 0; notes.append("description missing"); fixes.append("Add 'description'")
    else:
        if len(desc) > 1024: n = min(n, 1); notes.append("description > 1024 chars")
        if re.search(r"</?[A-Za-z][^>]*>", desc): n = min(n, 1); notes.append("description contains XML/HTML tags")
    dims.append(dim("frontmatter_validity", n, 2, notes, fixes))

    # 2. Description trigger quality (heuristic, max 2)
    n, notes, fixes = 2, [], []
    dl = desc.lower()
    if dl.startswith(("i ", "i'", "we ", "you ", "this skill")):
        n = min(n, 1); notes.append("not third person"); fixes.append("Rewrite in third person ('Generates…')")
    if not re.search(r"\b(use when|use this|when |for |run with|invoke |trigger|reach for|handy for|designed to|designed for|ideal for|helps with|helps to|handles)\b", dl):
        n = min(n, 1); notes.append("no explicit WHEN/trigger"); fixes.append("State when to use it (triggers)")
    if len(desc) < 60:
        n = min(n, 1); notes.append("very short / few trigger keywords"); fixes.append("Add concrete keywords a user would type")
    dims.append(dim("description_trigger_quality", n, 2, notes, fixes))

    # 3. Progressive disclosure / size (max 2)
    n, notes, fixes = 2, [], []
    nlines = body.count("\n") + 1
    has_refs = os.path.isdir(os.path.join(skill_dir, "references"))
    if nlines > 500:
        n = 0; notes.append(f"body {nlines} lines > 500"); fixes.append("Move depth into references/ and link by name")
    elif nlines > 400:
        n = min(n, 1); notes.append(f"body {nlines} lines (approaching 500)")
    if nlines > 300 and not has_refs:
        n = min(n, 1); notes.append("large body but no references/ offload")
    dims.append(dim("progressive_disclosure", n, 2, notes, fixes))

    # 4. Body concreteness (max 2)
    n, notes, fixes = 2, [], []
    has_steps = bool(re.search(r"^\s*\d+\.\s", body, re.M)) or "## steps" in body_lc or "## core process" in body_lc
    if not has_steps:
        n = min(n, 1); notes.append("no numbered/step structure"); fixes.append("Add numbered, actionable steps")
    vague_hits = [v for v in VAGUE if v in body_lc]
    if vague_hits:
        n = min(n, 1); notes.append(f"vague directives: {vague_hits[:3]}"); fixes.append("Replace with concrete, checkable actions")
    menu_hits = [m for m in MENU if m in body_lc]
    if len(menu_hits) >= 2:
        n = min(n, 1); notes.append("reads like a menu of options"); fixes.append("Give one default path; alternatives as fallback")
    dims.append(dim("body_concreteness", n, 2, notes, fixes))

    # 5. Discipline structure (informational, max 2 — only weighted for process skills)
    n, notes, fixes = 2, [], []
    has_verif = "## verification" in body_lc or re.search(r"- \[ \]", body)
    has_when = "## when to use" in body_lc
    if not has_when:
        n = min(n, 1); notes.append("no 'When to Use' section"); fixes.append("Add explicit triggers + exclusions")
    if not has_verif:
        n = min(n, 1); notes.append("no Verification checklist"); fixes.append("Add an evidence-based exit checklist (recommended for process skills)")
    dims.append(dim("structure_completeness", n, 2, notes, fixes))

    # 6. Script hygiene (max 2)
    n, notes, fixes = 2, [], []
    sdir = os.path.join(skill_dir, "scripts")
    scripts = []
    if os.path.isdir(sdir):
        for root, _, files in os.walk(sdir):
            for f in files:
                if f.endswith((".py", ".sh", ".cjs", ".js", ".ts")):
                    scripts.append(os.path.join(root, f))
    if scripts:
        for sp in scripts:
            raw = open(sp, encoding="utf-8", errors="ignore").read()
            code = strip_literals(raw).lower()
            if any(re.search(p, code) for p in INTERACTIVE):
                n = 0; notes.append(f"{os.path.basename(sp)} appears interactive"); fixes.append("Make scripts non-interactive (flags, not prompts)")
            if "print(" in code and "stderr" not in code and "json" not in code:
                n = min(n, 1); notes.append(f"{os.path.basename(sp)} may mix logs into stdout"); fixes.append("Route data→stdout, logs→stderr")
    else:
        notes.append("no scripts (fine for prose-only skills)")
    # Absolute path into a bundled dir = non-portable.
    if re.search(ABS_BUNDLED_RE, body):
        n = min(n, 1); notes.append("absolute path to a bundled file (breaks portability)")
        fixes.append("Reference bundled files relative to the skill dir (e.g. scripts/x.py)")
    dims.append(dim("script_hygiene", n, 2, notes, fixes))

    # 7. Trigger-eval coverage (max 2) — is the quality work a committed artifact?
    n, notes, fixes = 2, [], []
    ev_path = os.path.join(skill_dir, "evals", "trigger_evals.json")
    eval_stats = {"trigger": 0, "no_trigger": 0, "real": 0, "quadrants": {}, "splits": {}}
    if not os.path.isfile(ev_path):
        n = 0; notes.append("no evals/trigger_evals.json")
        fixes.append("Scaffold evals with skill-creator's new_evals.py, then fill real queries")
    else:
        try:
            ev = json.load(open(ev_path, encoding="utf-8"))
            qs = ev.get("queries") if isinstance(ev, dict) else ev
            qs = qs if isinstance(qs, list) else []
        except Exception:
            qs = None
        if qs is None:
            n = 0; notes.append("evals/trigger_evals.json is not valid JSON"); fixes.append("Fix the JSON")
        else:
            real = [q for q in qs if isinstance(q, dict)
                    and not str(q.get("query", "")).strip().upper().startswith("TODO")]
            trig = sum(1 for q in real if str(q.get("expect", "")).lower() == "trigger")
            notrig = sum(1 for q in real if str(q.get("expect", "")).lower() in ("no-trigger", "no_trigger"))
            quadrants = {}
            splits = {}
            for q in real:
                quad = q.get("quadrant")
                if quad:
                    quadrants[str(quad)] = quadrants.get(str(quad), 0) + 1
                sp = q.get("split")
                if sp:
                    splits[str(sp)] = splits.get(str(sp), 0) + 1

            eval_stats = {
                "trigger": trig,
                "no_trigger": notrig,
                "real": len(real),
                "quadrants": quadrants,
                "splits": splits
            }
            if not real:
                n = 0; notes.append("evals are only TODO placeholders"); fixes.append("Write real should-trigger / should-NOT-trigger queries")
            else:
                if notrig == 0:
                    n = min(n, 1); notes.append("no should-NOT-trigger cases"); fixes.append("Add near-miss queries that must NOT fire")
                if trig == 0:
                    n = min(n, 1); notes.append("no should-trigger cases"); fixes.append("Add colloquial queries that must fire")
                if len(real) < 10:
                    n = min(n, 1); notes.append(f"thin eval set ({len(real)} queries)"); fixes.append("Aim for ~16-20 queries, 8-10 per side across 4 quadrants")
                if quadrants:
                    notes.append(f"4-quadrant format ({len(quadrants)} quadrants)")
    dims.append(dim("trigger_eval_coverage", n, 2, notes, fixes))

    got = sum(d["score"] for d in dims)
    mx = sum(d["max"] for d in dims)
    return dims, {"got": got, "max": mx, "ratio": round(got / mx, 3), "eval_stats": eval_stats}


def grade(ratio):
    return ("A" if ratio >= .9 else "B" if ratio >= .8 else
            "C" if ratio >= .7 else "D" if ratio >= .6 else "F")


def main(argv):
    minr = 0.8
    args = argv[1:]
    pos, i = [], 0
    while i < len(args):
        a = args[i]
        if a == "--min":
            try: minr = float(args[i + 1])
            except Exception: pass
            i += 2; continue
        if a.startswith("--min="):
            try: minr = float(a.split("=", 1)[1])
            except Exception: pass
        elif not a.startswith("-"):
            pos.append(a)
        i += 1
    if len(pos) != 1:
        log("usage: score_skill.py <path/to/skill-dir-or-file.md> [--min 0.8]"); return 2
    d = pos[0]
    if not os.path.exists(d):
        log(f"error: not found: {d}"); return 2

    log(f"scoring {d} …")
    dims, tot = score(d)
    ratio = tot.get("ratio", 0.0)
    g = grade(ratio)
    all_fixes = [f for dd in dims for f in dd["fixes"]]
    for dd in dims:
        mark = "ok " if dd["score"] == dd["max"] else "!! "
        log(f"  {mark}{dd['dimension']}: {dd['score']}/{dd['max']}  {', '.join(dd['notes'])}")
    log(f"GRADE {g}  ({tot.get('got')}/{tot.get('max')} = {ratio})")
    out = {"grade": g, "ratio": ratio, "totals": tot, "dimensions": dims,
           "priority_fixes": all_fixes, "note": "Static rubric only — run dynamic trigger + baseline evals via SKILL.md."}
    print(json.dumps(out, indent=2))
    return 0 if ratio >= minr else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
