from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins/ihav-web-visit-counter/core/ihav-web-visit-counter"
sys.path.insert(0, str(CORE))

from ihav_web_visit_counter.errors import InvalidInputError
from ihav_web_visit_counter.normalize import normalize_domain


class NormalizeTests(unittest.TestCase):
    def test_url_path_and_www_are_removed(self):
        self.assertEqual(normalize_domain("https://WWW.Example.com/pricing?a=1"), "example.com")

    def test_other_subdomains_are_preserved(self):
        self.assertEqual(normalize_domain("blog.example.com"), "blog.example.com")

    def test_idn_is_ascii_normalized(self):
        self.assertEqual(normalize_domain("https://bücher.example/path"), "xn--bcher-kva.example")

    def test_incomplete_or_invalid_domain_is_rejected(self):
        for value in ("", "example", "bad domain.example", "-bad.example"):
            with self.subTest(value=value), self.assertRaises(InvalidInputError):
                normalize_domain(value)


if __name__ == "__main__":
    unittest.main()
