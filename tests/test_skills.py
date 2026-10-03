from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/ihav-web-visit-counter"


class SkillDocumentationTests(unittest.TestCase):
    def test_both_skills_preserve_the_same_result_rules(self):
        claude = (PLUGIN / "claude/skills/ihav-web-visit-counter/SKILL.md").read_text(encoding="utf-8")
        codex = (PLUGIN / "core/ihav-web-visit-counter/SKILL.md").read_text(encoding="utf-8")
        rules = (PLUGIN / "core/ihav-web-visit-counter/references/answer-rules.md").read_text(encoding="utf-8")
        for phrase in (
            "monthly visits are unknown",
            "third-party estimate",
            "analysis date",
            "no measured error interval",
            "stale",
            "Never average or merge",
            "HTTP 401, 403, 429",
            "Do not try another browser",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, claude)
                self.assertIn(phrase, codex)
        self.assertIn("`period` is `null`", rules)
        self.assertIn("These are timestamps, not reporting months", rules)
        self.assertIn("SimilarWeb among its upstreams", rules)
        self.assertIn("py -3", claude)
        self.assertIn("py -3", codex)

    def test_skill_reference_links_resolve(self):
        claude_rules = PLUGIN / "claude/skills/ihav-web-visit-counter/../../../core/ihav-web-visit-counter/references/answer-rules.md"
        codex_rules = PLUGIN / "core/ihav-web-visit-counter/references/answer-rules.md"
        self.assertTrue(claude_rules.resolve().is_file())
        self.assertTrue(codex_rules.is_file())


if __name__ == "__main__":
    unittest.main()
