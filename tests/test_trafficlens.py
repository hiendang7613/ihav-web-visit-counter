from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins/ihav-web-visit-counter/core/ihav-web-visit-counter"
sys.path.insert(0, str(CORE))

from ihav_web_visit_counter.errors import BlockedError
from ihav_web_visit_counter.models import result_from_dict
from ihav_web_visit_counter.providers import PROVIDERS, trafficlens, tranco, webtrafficchecker
from ihav_web_visit_counter.render import render
from ihav_web_visit_counter.service import lookup


def fixture(name: str) -> bytes:
    return (ROOT / "tests/fixtures/trafficlens" / name).read_bytes()


class TrafficLensTests(unittest.TestCase):
    def test_provider_chain_is_webtrafficchecker_trafficlens_then_tranco(self):
        self.assertEqual(PROVIDERS, (webtrafficchecker, trafficlens, tranco))

    def test_formatted_count_and_country_shares_are_preserved(self):
        with patch.object(trafficlens, "get_bytes", return_value=(200, fixture("count.json"), {})) as fetch:
            result = trafficlens.lookup("example.com", "https://example.com", cache=None)

        self.assertEqual(result.kind, "estimate")
        self.assertEqual(result.monthly_visits, "2.5M")
        self.assertIsNone(result.period)
        self.assertIsNone(result.analyzed_at)
        self.assertEqual(result.scraped_at, "2026-10-02T12:00:00.000Z")
        self.assertFalse(result.stale)
        self.assertEqual(result.countries[0]["country"], "United States")
        self.assertAlmostEqual(result.countries[0]["share"], 0.421)
        self.assertEqual(result.source["name"], "TrafficLens")
        self.assertEqual(result.source["layer"], "fallback")
        fetch.assert_called_once_with(
            "https://traffic-lens-api.admin-d10.workers.dev/api/analyze/example.com",
            "application/json",
        )

    def test_stale_value_renders_raw_approximate_count_and_scrape_date(self):
        with patch.object(trafficlens, "get_bytes", return_value=(200, fixture("stale-github.json"), {})):
            result = trafficlens.lookup("github.com", "github.com", cache=None)

        output = render(result)
        self.assertEqual(result.monthly_visits, "631.0M")
        self.assertTrue(result.stale)
        self.assertEqual(result.scraped_at, "2026-06-04T04:46:23.619Z")
        self.assertIsNone(result.period)
        self.assertIn("~631.0M estimated monthly visits · stale · scraped 2026-06-04", output)
        self.assertNotIn("631,000,000", output)
        self.assertNotIn("analyzed 2026-06-04", output)

    def test_rank_only_payload_is_skipped_so_tranco_can_answer(self):
        archive = (ROOT / "tests/fixtures/tranco/top-1m.csv.zip").read_bytes()
        calls = []

        def primary(*_args):
            calls.append("WebTrafficChecker")
            return None

        def trafficlens_response(*_args):
            calls.append("TrafficLens")
            return 200, fixture("rank-only-python.json"), {}

        def tranco_response(*_args, **_kwargs):
            calls.append("Tranco")
            return 200, archive, {}

        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(webtrafficchecker, "lookup", side_effect=primary):
                with patch.object(trafficlens, "get_bytes", side_effect=trafficlens_response):
                    with patch.object(tranco, "get_bytes", side_effect=tranco_response):
                        result = lookup("python.org", Path(temporary))

        self.assertEqual(calls, ["WebTrafficChecker", "TrafficLens", "Tranco"])
        self.assertEqual(result.kind, "rank_only")
        self.assertIsNone(result.monthly_visits)
        self.assertEqual(result.source["name"], "Tranco")
        self.assertTrue(any("TrafficLens returned no usable result" in note for note in result.notes))

    def test_blocked_primary_uses_stale_trafficlens_then_caches_estimate(self):
        calls = []

        def blocked_primary(*_args):
            calls.append("WebTrafficChecker")
            raise BlockedError("HTTP 403; stopped", "webtrafficchecker.com")

        def trafficlens_response(*_args):
            calls.append("TrafficLens")
            return 200, fixture("stale-github.json"), {}

        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(webtrafficchecker, "lookup", side_effect=blocked_primary):
                with patch.object(trafficlens, "get_bytes", side_effect=trafficlens_response) as fetch:
                    with patch.object(tranco, "lookup") as rank_fallback:
                        first = lookup("github.com", Path(temporary))
                        second = lookup("github.com", Path(temporary))

        self.assertEqual(calls, ["WebTrafficChecker", "TrafficLens"])
        fetch.assert_called_once()
        rank_fallback.assert_not_called()
        self.assertEqual(first.source["name"], "TrafficLens")
        self.assertTrue(any("WebTrafficChecker failed" in note for note in first.notes))
        self.assertTrue(second.cached)
        self.assertEqual(second.monthly_visits, "631.0M")
        self.assertTrue(second.stale)

    def test_old_cached_result_shape_remains_readable(self):
        body = (ROOT / "tests/fixtures/webtrafficchecker/github.json").read_bytes()
        with patch.object(webtrafficchecker, "get_bytes", return_value=(200, body, {})):
            result = webtrafficchecker.lookup("github.com", "github.com")
        old_shape = result.to_dict()
        old_shape.pop("scraped_at")
        old_shape.pop("stale")

        restored = result_from_dict(old_shape)

        self.assertEqual(restored.monthly_visits, result.monthly_visits)
        self.assertIsNone(restored.scraped_at)
        self.assertFalse(restored.stale)

    def test_non_count_and_mismatched_domains_are_ignored(self):
        invalid = json.loads(fixture("count.json"))
        invalid["monthlyVisits"] = "631 million visitors"
        with patch.object(trafficlens, "get_bytes", return_value=(200, json.dumps(invalid).encode(), {})):
            self.assertIsNone(trafficlens.lookup("example.com", "example.com", cache=None))

        mismatch = json.loads(fixture("count.json"))
        mismatch["domain"] = "other.example"
        with patch.object(trafficlens, "get_bytes", return_value=(200, json.dumps(mismatch).encode(), {})):
            self.assertIsNone(trafficlens.lookup("example.com", "example.com", cache=None))

    def test_blocked_worker_request_is_not_retried(self):
        blocked = BlockedError("HTTP 403; stopped", "traffic-lens-api.admin-d10.workers.dev")
        with patch.object(trafficlens, "get_bytes", side_effect=blocked) as fetch:
            with self.assertRaises(BlockedError):
                trafficlens.lookup("github.com", "github.com", cache=None)
        fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
