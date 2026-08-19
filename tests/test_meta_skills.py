# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Comprehensive test suite for meta-skills plugin scripts."""

import unittest
import tempfile
import shutil
import os
import sys
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "skill-creator", "scripts"))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "skill-evaluator", "scripts"))

import validate_skill
import score_skill
import new_skill
import new_evals


class TestFrontmatterParsing(unittest.TestCase):
    def test_parse_standard_frontmatter(self):
        text = "---\nname: my-skill\ndescription: A great skill. Use when needed.\n---\n# Body\nContent"
        fm, body = validate_skill.parse_frontmatter(text)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "my-skill")
        self.assertEqual(fm["description"], "A great skill. Use when needed.")
        self.assertIn("# Body", body)

    def test_parse_extended_frontmatter(self):
        text = """---
name: tool-skill
description: Tool execution skill. Use when tools are requested.
disable-model-invocation: true
allowed-tools: [Bash, ReadFile]
compatibility: ">=3.9"
metadata: custom-data
---
# Content
"""
        fm, body = validate_skill.parse_frontmatter(text)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "tool-skill")
        self.assertTrue(fm["disable-model-invocation"])
        self.assertEqual(fm["allowed-tools"], ["Bash", "ReadFile"])
        self.assertEqual(fm["compatibility"], ">=3.9")
        self.assertEqual(fm["metadata"], "custom-data")

    def test_score_skill_parse_frontmatter(self):
        text = "---\nname: test-score\ndescription: Test. Use when testing.\ndisable-model-invocation: false\n---\n# Body"
        fm, body = score_skill.parse_frontmatter(text)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "test-score")
        self.assertFalse(fm["disable-model-invocation"])


class TestValidationRules(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _write_skill(self, name, description):
        sdir = os.path.join(self.test_dir, name)
        os.makedirs(os.path.join(sdir, "evals"), exist_ok=True)
        os.makedirs(os.path.join(sdir, "references"), exist_ok=True)
        with open(os.path.join(sdir, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write(f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n\n## When to Use\nUse when needed.\n\n## Core Process\n1. Do task.\n\n## Verification\n- [ ] done\n")
        with open(os.path.join(sdir, "evals", "trigger_evals.json"), "w", encoding="utf-8") as fh:
            json.dump({
                "queries": [
                    {"query": f"run {name} for task", "expect": "trigger"},
                    {"query": f"run {name} for task 2", "expect": "trigger"},
                    {"query": f"run {name} for task 3", "expect": "trigger"},
                    {"query": f"run {name} for task 4", "expect": "trigger"},
                    {"query": f"run {name} for task 5", "expect": "trigger"},
                    {"query": "unrelated task 1", "expect": "no-trigger"},
                    {"query": "unrelated task 2", "expect": "no-trigger"},
                    {"query": "unrelated task 3", "expect": "no-trigger"},
                    {"query": "unrelated task 4", "expect": "no-trigger"},
                    {"query": "unrelated task 5", "expect": "no-trigger"},
                ]
            }, fh)
        return sdir

    def test_reserved_words_allows_substrings(self):
        # "misanthropic" contains "anthropic" as substring, but is NOT the reserved word "anthropic"
        sdir = self._write_skill("misanthropic-detector", "Detects misanthropic sentiments. Use when analyzing text for cynicism.")
        errs, warns, _ = validate_skill.validate(sdir)
        self.assertEqual(errs, [])

        # Branded name with reserved segment must fail
        sdir_bad = self._write_skill("anthropic-runner", "Runs Anthropic models. Use when running Claude models.")
        errs_bad, _, _ = validate_skill.validate(sdir_bad)
        self.assertTrue(any("reserved words" in e for e in errs_bad))

    def test_description_allows_math_inequalities(self):
        # Inequality operators should not be rejected as XML tags
        sdir = self._write_skill("range-checker", "Checks if latency is > 10ms and < 500ms. Use when tuning pipeline latency.")
        errs, warns, _ = validate_skill.validate(sdir)
        self.assertEqual(errs, [])

        # Actual HTML tag should be rejected
        sdir_bad = self._write_skill("html-skill", "Checks ranges <script>alert(1)</script>. Use when analyzing code.")
        errs_bad, _, _ = validate_skill.validate(sdir_bad)
        self.assertTrue(any("XML/HTML tags" in e for e in errs_bad))

    def test_description_natural_trigger_phrasing(self):
        # Alternative trigger phrasings like "Reach for this..." should pass without errors
        sdir = self._write_skill("pdf-parser", "Extracts structured tables from PDFs. Reach for this to extract financial statement tables.")
        errs, warns, _ = validate_skill.validate(sdir)
        self.assertEqual(errs, [])
        self.assertEqual(warns, [])


class TestPathRegex(unittest.TestCase):
    def test_abs_bundled_re_matches_absolute_paths(self):
        self.assertTrue(bool(validate_skill.ABS_BUNDLED_RE.search("/home/user/project/scripts/run.py")))
        self.assertTrue(bool(validate_skill.ABS_BUNDLED_RE.search("`C:\\Users\\user\\project\\references\\doc.md`")))
        self.assertTrue(bool(validate_skill.ABS_BUNDLED_RE.search(r"\\server\share\assets\logo.png")))
        self.assertTrue(bool(validate_skill.ABS_BUNDLED_RE.search("--dir=/home/user/project/scripts/run.py")))
        self.assertTrue(bool(validate_skill.ABS_BUNDLED_RE.search("key: /home/user/references/doc.md")))
        self.assertTrue(bool(validate_skill.ABS_BUNDLED_RE.search("[script](/home/user/scripts/run.py)")))
        self.assertTrue(bool(score_skill.ABS_BUNDLED_RE.search("/home/user/project/scripts/run.py")))

    def test_abs_bundled_re_ignores_relative_paths_and_urls(self):
        self.assertFalse(bool(validate_skill.ABS_BUNDLED_RE.search("skills/deep-news-researcher/scripts/date_validator.py")))
        self.assertFalse(bool(validate_skill.ABS_BUNDLED_RE.search("`skills/my-skill/references/guide.md`")))
        self.assertFalse(bool(validate_skill.ABS_BUNDLED_RE.search("python scripts/validate_skill.py")))
        self.assertFalse(bool(validate_skill.ABS_BUNDLED_RE.search("references/cookbook.md")))
        self.assertFalse(bool(validate_skill.ABS_BUNDLED_RE.search("https://github.com/org/repo/scripts/foo.py")))
        self.assertFalse(bool(validate_skill.ABS_BUNDLED_RE.search("http://example.com/assets/img.png")))
        self.assertFalse(bool(score_skill.ABS_BUNDLED_RE.search("skills/my-skill/scripts/run.py")))


class TestWorkspaceAuditing(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_skill(self, name, description, extra_frontmatter="", body_extra=""):
        sdir = os.path.join(self.test_dir, name)
        os.makedirs(os.path.join(sdir, "evals"), exist_ok=True)
        os.makedirs(os.path.join(sdir, "references"), exist_ok=True)
        md_content = f"""---
name: {name}
description: {description}
{extra_frontmatter}
---
# {name}

## When to Use
Use when required.

## Core Process
1. Step one.
2. Step two.

## Verification
- [ ] Task completed.
{body_extra}
"""
        with open(os.path.join(sdir, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write(md_content)

        evals_data = {
            "skill": name,
            "queries": [
                {"query": f"run {name} for my first task", "expect": "trigger", "split": "train"},
                {"query": f"execute {name} workflow in production", "expect": "trigger", "split": "train"},
                {"query": f"please invoke {name} to process data", "expect": "trigger", "split": "val"},
                {"query": f"unrelated query for completely different task A", "expect": "no-trigger", "split": "train"},
                {"query": f"unrelated query for completely different task B", "expect": "no-trigger", "split": "train"},
                {"query": f"unrelated query for completely different task C", "expect": "no-trigger", "split": "val"},
            ]
        }
        with open(os.path.join(sdir, "evals", "trigger_evals.json"), "w", encoding="utf-8") as fh:
            json.dump(evals_data, fh)
        return sdir

    def test_audit_clean_workspace(self):
        self.create_skill("skill-a", "Manages database backups. Use when the user requests database backup or archiving.")
        self.create_skill("skill-b", "Generates React frontend components. Use when the user requests UI components or React views.")
        
        errs, warns, facts = validate_skill.validate(os.path.join(self.test_dir, "skill-a"))
        self.assertEqual(len(errs), 0)

        # Audit workspace
        exit_code = validate_skill.audit_workspace(self.test_dir, strict=True)
        self.assertEqual(exit_code, 0)

    def test_audit_detects_duplicate_names(self):
        dir1 = os.path.join(self.test_dir, "sub1")
        dir2 = os.path.join(self.test_dir, "sub2")
        os.makedirs(dir1); os.makedirs(dir2)
        
        # Create identical skill name in two different directories
        s1 = os.path.join(dir1, "dup-skill")
        s2 = os.path.join(dir2, "dup-skill")
        for s in (s1, s2):
            os.makedirs(os.path.join(s, "evals"), exist_ok=True)
            with open(os.path.join(s, "SKILL.md"), "w", encoding="utf-8") as fh:
                fh.write("---\nname: dup-skill\ndescription: Duplicate. Use when duplicating.\n---\n## When to Use\n## Verification\n- [ ] ok")
            with open(os.path.join(s, "evals", "trigger_evals.json"), "w", encoding="utf-8") as fh:
                json.dump({"queries": [{"query": "t", "expect": "trigger"}, {"query": "nt", "expect": "no-trigger"}]}, fh)

        exit_code = validate_skill.audit_workspace(self.test_dir, strict=False)
        self.assertEqual(exit_code, 1)

    def test_audit_calibrated_trigger_collision(self):
        # Two skills with high keyword overlap
        self.create_skill("docker-deployer", "Deploys containerized web applications. Use when deploying docker container clusters and running release orchestration.")
        self.create_skill("docker-runner", "Runs containerized docker applications. Use when running docker container clusters and deploying container releases.")

        # Under strict mode, advisory collision warnings do not crash CI if skills themselves are valid
        exit_code = validate_skill.audit_workspace(self.test_dir, strict=True, fail_on_collision=False)
        self.assertEqual(exit_code, 0)

        # When fail_on_collision is explicitly requested, it fails
        exit_code_fail = validate_skill.audit_workspace(self.test_dir, strict=True, fail_on_collision=True)
        self.assertEqual(exit_code_fail, 1)

    def test_audit_cli_fail_on_collision_flag(self):
        self.create_skill("docker-deployer", "Deploys containerized web applications. Use when deploying docker container clusters and running release orchestration.")
        self.create_skill("docker-runner", "Runs containerized docker applications. Use when running docker container clusters and deploying container releases.")

        # CLI invocation without --fail-on-collision succeeds (exit code 0)
        code_default = validate_skill.main(["validate_skill.py", "--audit-workspace", self.test_dir])
        self.assertEqual(code_default, 0)

        # CLI invocation with --fail-on-collision returns 1
        code_fail = validate_skill.main(["validate_skill.py", "--audit-workspace", self.test_dir, "--fail-on-collision"])
        self.assertEqual(code_fail, 1)


class TestScaffoldingTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_new_skill_and_new_evals(self):
        skill_name = "test-scaffold"
        res = new_skill.main(["new_skill.py", skill_name, "--dir", self.test_dir])
        self.assertEqual(res, 0)

        skill_dir = os.path.join(self.test_dir, skill_name)
        self.assertTrue(os.path.isfile(os.path.join(skill_dir, "SKILL.md")))
        evals_file = os.path.join(skill_dir, "evals", "trigger_evals.json")
        self.assertTrue(os.path.isfile(evals_file))

        with open(evals_file, encoding="utf-8") as fh:
            data = json.load(fh)
            self.assertEqual(data["skill"], skill_name)
            # Verify 4-quadrant structure exists in scaffold
            quadrants = [q.get("quadrant") for q in data["queries"] if "quadrant" in q]
            self.assertIn("Q1_direct", quadrants)
            self.assertIn("Q2_colloquial", quadrants)
            self.assertIn("Q3_near_miss", quadrants)
            self.assertIn("Q4_sibling_adjacent", quadrants)

            # Verify train and val splits exist in scaffold
            splits = {q.get("split") for q in data["queries"] if "split" in q}
            self.assertIn("train", splits)
            self.assertIn("val", splits)


class TestSelfValidationAndScoring(unittest.TestCase):
    def test_self_validate_all_skills(self):
        skills_dir = os.path.join(REPO_ROOT, "skills")
        for sname in ("skill-creator", "skill-evaluator"):
            sdir = os.path.join(skills_dir, sname)
            errs, warns, facts = validate_skill.validate(sdir)
            self.assertEqual(errs, [], f"Validation errors in {sname}: {errs}")
            self.assertEqual(warns, [], f"Validation warnings in {sname}: {warns}")

    def test_self_score_and_dogfooding(self):
        skills_dir = os.path.join(REPO_ROOT, "skills")
        for sname in ("skill-creator", "skill-evaluator"):
            sdir = os.path.join(skills_dir, sname)
            dims, tot = score_skill.score(sdir)
            grade = score_skill.grade(tot["ratio"])
            self.assertEqual(grade, "A", f"Score grade for {sname} was {grade} (got {tot['got']}/{tot['max']})")
            self.assertEqual(tot["got"], 14, f"{sname} lost points on dimensions: {dims}")

            # Verify 4-quadrant dogfooding
            eval_stats = tot.get("eval_stats", {})
            quadrants = eval_stats.get("quadrants", {})
            self.assertIn("Q1_direct", quadrants, f"{sname} missing Q1_direct evals")
            self.assertIn("Q2_colloquial", quadrants, f"{sname} missing Q2_colloquial evals")
            self.assertIn("Q3_near_miss", quadrants, f"{sname} missing Q3_near_miss evals")
            self.assertIn("Q4_sibling_adjacent", quadrants, f"{sname} missing Q4_sibling_adjacent evals")

            splits = eval_stats.get("splits", {})
            self.assertIn("train", splits, f"{sname} missing train split")
            self.assertIn("val", splits, f"{sname} missing val split")

    def test_workspace_audit_skills_dir(self):
        skills_dir = os.path.join(REPO_ROOT, "skills")
        exit_code = validate_skill.audit_workspace(skills_dir, strict=True)
        self.assertEqual(exit_code, 0, "Workspace audit failed on repo skills/ directory")


if __name__ == "__main__":
    unittest.main()
