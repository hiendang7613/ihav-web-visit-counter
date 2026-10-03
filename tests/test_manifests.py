from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/ihav-web-visit-counter"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ManifestTests(unittest.TestCase):
    def test_host_manifests_share_name_version_and_license(self):
        claude = load(PLUGIN / ".claude-plugin/plugin.json")
        codex = load(PLUGIN / ".codex-plugin/plugin.json")
        self.assertEqual(claude["name"], codex["name"])
        self.assertEqual(claude["name"], "ihav-web-visit-counter")
        self.assertEqual(claude["version"], codex["version"])
        self.assertEqual(claude["version"], "0.1.0")
        self.assertEqual(claude["license"], codex["license"])
        self.assertEqual(claude["license"], "MIT")
        self.assertIn("TrafficLens", codex["interface"]["longDescription"])
        self.assertNotIn("reporting period", codex["interface"]["longDescription"].lower())

    def test_both_marketplaces_point_to_the_plugin_and_skill_paths_exist(self):
        claude_market = load(ROOT / ".claude-plugin/marketplace.json")
        codex_market = load(ROOT / ".agents/plugins/marketplace.json")
        self.assertEqual(claude_market["plugins"][0]["name"], "ihav-web-visit-counter")
        self.assertEqual(claude_market["plugins"][0]["source"], "./plugins/ihav-web-visit-counter")
        self.assertEqual(codex_market["plugins"][0]["name"], "ihav-web-visit-counter")
        self.assertEqual(codex_market["plugins"][0]["source"]["path"], "./plugins/ihav-web-visit-counter")
        self.assertTrue((PLUGIN / "claude/skills/ihav-web-visit-counter/SKILL.md").is_file())
        self.assertTrue((PLUGIN / "core/ihav-web-visit-counter/SKILL.md").is_file())
        self.assertFalse((ROOT / "skills").exists())
        self.assertIn("analysis date", claude_market["plugins"][0]["description"])


if __name__ == "__main__":
    unittest.main()
