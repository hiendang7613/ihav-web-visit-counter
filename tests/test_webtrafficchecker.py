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

    def _lookup_payload(self, payload):
        body = json.dumps(payload).encode("utf-8")
        domain = payload.get("domain", "example.com")
        with patch.object(webtrafficchecker, "get_bytes", return_value=(200, body, {"content-type": "application/json"})):
            return webtrafficchecker.lookup(domain, domain)

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

    def test_ranked_response_with_true_flag_keeps_its_estimate(self):
        payload = json.loads(self.fixture)
        payload["traffic"]["isRanked"] = True

        result = self._lookup_payload(payload)

        self.assertEqual(result.kind, "estimate")
        self.assertEqual(result.monthly_visits, 486200000)
        self.assertEqual(result.rank["value"], 20)

    def test_missing_analysis_timestamp_does_not_return_a_number(self):
        payload = json.loads(self.fixture)
        del payload["analyzedAt"]
        with patch.object(webtrafficchecker, "get_bytes", return_value=(200, json.dumps(payload).encode(), {})):
            self.assertIsNone(webtrafficchecker.lookup("github.com", "github.com"))

    def test_unranked_placeholder_fixture_is_not_a_visit_estimate(self):
        payload = json.loads(
            (ROOT / "tests/fixtures/webtrafficchecker/unranked.json").read_text(encoding="utf-8")
        )

        self.assertEqual(payload["traffic"]["monthlyVisits"], 65)
        self.assertFalse(payload["traffic"]["isRanked"])
        self.assertEqual(payload["traffic"]["globalRank"], 0)
        self.assertEqual(payload["traffic"]["category"], "Unranked Website")
        self.assertIsNone(self._lookup_payload(payload))

    def test_each_unranked_signal_rejects_placeholder_visits(self):
        baseline = json.loads(self.fixture)
        cases = [
            ("isRanked false", {"isRanked": False, "globalRank": 20, "category": "Technology"}, False),
            ("zero rank", {"isRanked": True, "globalRank": 0, "category": "Technology"}, False),
            ("null rank", {"isRanked": True, "globalRank": None, "category": "Technology"}, False),
            ("missing rank", {"isRanked": True, "category": "Technology"}, True),
            ("unranked category", {"isRanked": True, "globalRank": 20, "category": "Unranked Website"}, False),
        ]

        for label, traffic_fields, remove_rank in cases:
            with self.subTest(label=label):
                payload = json.loads(json.dumps(baseline))
                payload["traffic"].update(traffic_fields)
                if remove_rank:
                    payload["traffic"].pop("globalRank")
                self.assertIsNone(self._lookup_payload(payload))

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
