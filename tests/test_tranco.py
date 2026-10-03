from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins/ihav-web-visit-counter/core/ihav-web-visit-counter"
sys.path.insert(0, str(CORE))

from ihav_web_visit_counter.cache import Cache
from ihav_web_visit_counter.providers import tranco


class TrancoTests(unittest.TestCase):
    def setUp(self):
        self.fixture = (ROOT / "tests/fixtures/tranco/top-1m.csv.zip").read_bytes()

    def test_saved_daily_archive_is_searched_locally(self):
        self.assertEqual(tranco.rank_in_list(self.fixture, "github.com"), 20)
        self.assertEqual(tranco.rank_in_list(self.fixture, "missing.example"), None)

    def test_cache_makes_one_daily_list_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Cache(Path(temporary))
            with patch.object(tranco, "get_bytes", return_value=(200, self.fixture, {})) as fetch:
                first = tranco.lookup("github.com", "github.com", cache)
                second = tranco.lookup("python.org", "python.org", cache)
            fetch.assert_called_once_with(
                tranco.LIST_URL,
                "application/zip, text/csv;q=0.9, */*;q=0.1",
                redirect_host="tranco-list.eu",
            )
        self.assertEqual(first.rank["value"], 20)
        self.assertEqual(second.rank["value"], 640)
        self.assertEqual(first.source["layer"], "fallback")
        self.assertIsNone(first.monthly_visits)


if __name__ == "__main__":
    unittest.main()
