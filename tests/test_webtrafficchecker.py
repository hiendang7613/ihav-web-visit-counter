from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins/ihav-web-visit-counter/core/ihav-web-visit-counter"
sys.path.insert(0, str(CORE))

from ihav_web_visit_counter.providers import webtrafficchecker


class WebTrafficCheckerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = (ROOT / "tests/fixtures/webtrafficchecker/github.json").read_bytes()

    def test_fixture_maps_to_estimate_without_claiming_a_reporting_period(self):
        with patch.object(webtrafficchecker, "get_bytes", return_value=(200, self.fixture, {"content-type": "application/json"})) as fetch:
            result = webtrafficchecker.lookup("github.com", "https://github.com")

        fetch.assert_called_once()
        self.assertIn("domain=github.com", fetch.call_args.args[0])
        self.assertEqual(result.kind, "estimate")
        self.assertEqual(result.monthly_visits, 486200000)
        self.assertEqual(result.monthly_visits_text, "486,200,000")
        self.assertIsNone(result.period)
        self.assertEqual(result.analyzed_at, "2026-09-11T12:00:00.000Z")
        self.assertEqual(result.rank["value"], 20)
        self.assertAlmostEqual(result.countries[0]["share"], 0.242)
        self.assertEqual([row["date"] for row in result.history], ["2026-08-13", "2026-09-11"])
        self.assertIn("webtrafficchecker.com", result.source["url"])
        self.assertIsNone(result.range)

    def test_missing_analysis_timestamp_does_not_return_a_number(self):
        payload = json.loads(self.fixture)
        del payload["analyzedAt"]
        with patch.object(webtrafficchecker, "get_bytes", return_value=(200, json.dumps(payload).encode(), {})):
            self.assertIsNone(webtrafficchecker.lookup("github.com", "github.com"))

    def test_history_keeps_latest_snapshot_per_month_and_sorts_dates(self):
        history = webtrafficchecker._history(
            [
                {"date": "2026-09-30", "visits": 900},
                {"date": "2026-08-13", "visits": 400},
                {"date": "2026-09-01", "visits": 100},
            ]
        )
        self.assertEqual(
            history,
            [
                {"date": "2026-08-13", "visits": 400},
                {"date": "2026-09-30", "visits": 900},
            ],
        )


if __name__ == "__main__":
    unittest.main()
