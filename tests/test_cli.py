from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins/ihav-web-visit-counter/core/ihav-web-visit-counter"
sys.path.insert(0, str(CORE))

from ihav_web_visit_counter import cli
from ihav_web_visit_counter.errors import BlockedError, ProviderError
from ihav_web_visit_counter.providers import trafficlens, webtrafficchecker
from ihav_web_visit_counter.service import lookup


def fixture_result():
    body = (ROOT / "tests/fixtures/webtrafficchecker/github.json").read_bytes()
    with patch.object(webtrafficchecker, "get_bytes", return_value=(200, body, {})):
        return webtrafficchecker.lookup("github.com", "github.com")


class CliTests(unittest.TestCase):
    def test_cli_returns_contract_json_then_readable_cached_card(self):
        result = fixture_result()
        with tempfile.TemporaryDirectory() as temporary:
            with patch("ihav_web_visit_counter.providers.webtrafficchecker.lookup", return_value=result) as primary:
                json_out = StringIO()
                with redirect_stdout(json_out):
                    json_code = cli.main(["https://github.com", "--json", "--cache-dir", temporary])
                human_out = StringIO()
                with redirect_stdout(human_out):
                    human_code = cli.main(["github.com", "--cache-dir", temporary])

        payload = json.loads(json_out.getvalue())
        self.assertEqual(json_code, 0)
        self.assertEqual(human_code, 0)
        self.assertEqual(payload["kind"], "estimate")
        self.assertIsInstance(payload["monthly_visits"], int)
        self.assertEqual(payload["monthly_visits"], 486200000)
        self.assertEqual(payload["monthly_visits_text"], "486,200,000")
        self.assertIsNone(payload["period"])
        self.assertEqual(payload["analyzed_at"], "2026-09-11T12:00:00.000Z")
        self.assertEqual(primary.call_count, 1)
        self.assertIn("estimated monthly visits · analyzed 2026-09-11", human_out.getvalue())
        self.assertIn("Error range: not independently measured", human_out.getvalue())
        self.assertIn("History snapshots 2026-08-13 → 2026-09-11", human_out.getvalue())
        self.assertIn("Cached result", human_out.getvalue())
        self.assertIn("webtrafficchecker.com", human_out.getvalue())

    def test_cli_rejects_invalid_input_without_provider_calls(self):
        stderr = StringIO()
        with tempfile.TemporaryDirectory() as temporary:
            with patch("ihav_web_visit_counter.providers.webtrafficchecker.lookup") as primary:
                with patch("ihav_web_visit_counter.providers.trafficlens.lookup") as middle:
                    with patch("ihav_web_visit_counter.providers.tranco.lookup") as fallback:
                        with redirect_stderr(stderr):
                            exit_code = cli.main(["not a domain", "--cache-dir", temporary])
        primary.assert_not_called()
        middle.assert_not_called()
        fallback.assert_not_called()
        self.assertEqual(exit_code, 64)
        self.assertIn("enter a website", stderr.getvalue().lower())

    def test_blocked_primary_runs_tranco_once_and_returns_rank_with_reason(self):
        stdout = StringIO()
        archive = (ROOT / "tests/fixtures/tranco/top-1m.csv.zip").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            with patch("ihav_web_visit_counter.providers.webtrafficchecker.lookup", side_effect=BlockedError("HTTP 403; stopped", "webtrafficchecker.com")):
                with patch("ihav_web_visit_counter.providers.trafficlens.lookup", return_value=None):
                    with patch("ihav_web_visit_counter.providers.tranco.get_bytes", return_value=(200, archive, {})) as fetch:
                        with redirect_stdout(stdout):
                            exit_code = cli.main(["github.com", "--json", "--cache-dir", temporary])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "rank_only")
        self.assertIsNone(payload["monthly_visits"])
        self.assertIsNone(payload["monthly_visits_text"])
        self.assertIn("HTTP 403", " ".join(payload["notes"]))
        fetch.assert_called_once()

    def test_both_sources_failing_keeps_primary_status_and_reports_fallback(self):
        stdout = StringIO()
        with tempfile.TemporaryDirectory() as temporary:
            with patch("ihav_web_visit_counter.providers.webtrafficchecker.lookup", side_effect=BlockedError("HTTP 403; stopped", "webtrafficchecker.com")):
                with patch("ihav_web_visit_counter.providers.trafficlens.lookup", return_value=None):
                    with patch("ihav_web_visit_counter.providers.tranco.lookup", side_effect=ProviderError("Tranco download failed", "Tranco")):
                        with redirect_stdout(stdout):
                            exit_code = cli.main(["github.com", "--json", "--cache-dir", temporary])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 4)
        self.assertEqual(payload["error"]["code"], "blocked")
        self.assertIn("Tranco failed", payload["error"]["message"])

    def test_primary_provider_error_also_runs_fallback(self):
        archive = (ROOT / "tests/fixtures/tranco/top-1m.csv.zip").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            with patch("ihav_web_visit_counter.providers.webtrafficchecker.lookup", side_effect=ProviderError("primary unavailable", "WebTrafficChecker")):
                with patch("ihav_web_visit_counter.providers.trafficlens.lookup", return_value=None):
                    with patch("ihav_web_visit_counter.providers.tranco.get_bytes", return_value=(200, archive, {})):
                        result = lookup("github.com", Path(temporary))
        self.assertEqual(result.kind, "rank_only")
        self.assertIn("primary unavailable", " ".join(result.notes))

    def test_service_falls_back_to_rank_only_and_caches_the_downloaded_archive(self):
        archive = (ROOT / "tests/fixtures/tranco/top-1m.csv.zip").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            with patch("ihav_web_visit_counter.providers.webtrafficchecker.lookup", return_value=None) as primary:
                with patch("ihav_web_visit_counter.providers.trafficlens.lookup", return_value=None):
                    with patch("ihav_web_visit_counter.providers.tranco.get_bytes", return_value=(200, archive, {})) as fetch:
                        result = lookup("python.org", Path(temporary))
                        cached = lookup("python.org", Path(temporary))

        self.assertEqual(primary.call_count, 2)
        fetch.assert_called_once()
        self.assertEqual(result.kind, "rank_only")
        self.assertIsNone(result.monthly_visits)
        self.assertIsNone(result.period)
        self.assertIsNone(result.analyzed_at)
        self.assertEqual(result.rank["value"], 640)
        self.assertEqual(result.source["name"], "Tranco")
        self.assertFalse(cached.cached)
        self.assertEqual(cached.kind, "rank_only")

    def test_missing_primary_timestamp_falls_back_instead_of_showing_a_number(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch("ihav_web_visit_counter.providers.webtrafficchecker.lookup", return_value=None):
                with patch("ihav_web_visit_counter.providers.trafficlens.lookup", return_value=None):
                    with patch("ihav_web_visit_counter.providers.tranco.lookup", return_value=None):
                        stderr = StringIO()
                        with redirect_stderr(stderr):
                            exit_code = cli.main(["github.com", "--cache-dir", temporary])
        self.assertEqual(exit_code, 2)
        self.assertIn("no visits were inferred", stderr.getvalue().lower())
        self.assertNotIn("WebTrafficChecker", stderr.getvalue())
        self.assertNotIn("Tranco", stderr.getvalue())

    def test_unranked_placeholder_falls_through_and_unknown_domain_exits_no_data(self):
        fixture = (ROOT / "tests/fixtures/webtrafficchecker/unranked.json").read_bytes()
        stdout = StringIO()
        stderr = StringIO()
        with tempfile.TemporaryDirectory() as temporary:
            with patch(
                "ihav_web_visit_counter.providers.webtrafficchecker.get_bytes",
                return_value=(200, fixture, {"content-type": "application/json"}),
            ):
                with patch("ihav_web_visit_counter.providers.trafficlens.lookup", return_value=None) as middle:
                    with patch("ihav_web_visit_counter.providers.tranco.lookup", return_value=None) as fallback:
                        with redirect_stdout(stdout), redirect_stderr(stderr):
                            exit_code = cli.main(
                                ["ihav-no-such-site-48213.com", "--json", "--cache-dir", temporary]
                            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["error"]["code"], "no_data")
        self.assertIn("no visits were inferred", payload["error"]["message"])
        self.assertNotIn("monthly_visits", payload)
        self.assertNotIn("countries", payload)
        self.assertNotIn("65", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")
        middle.assert_called_once()
        fallback.assert_called_once()

    def test_unexpected_exception_returns_stable_json_without_traceback(self):
        stdout = StringIO()
        stderr = StringIO()
        with tempfile.TemporaryDirectory() as temporary:
            with patch("ihav_web_visit_counter.providers.webtrafficchecker.lookup", side_effect=RuntimeError("secret detail")):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = cli.main(["github.com", "--json", "--cache-dir", temporary])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 5)
        self.assertEqual(payload["error"]["code"], "internal_error")
        self.assertNotIn("secret detail", stdout.getvalue() + stderr.getvalue())
        self.assertNotIn("Traceback", stdout.getvalue() + stderr.getvalue())

    def test_unavailable_cache_does_not_hide_a_primary_result(self):
        result = fixture_result()
        with tempfile.TemporaryDirectory() as temporary:
            cache_root = Path(temporary) / "not-a-directory"
            cache_root.write_text("file", encoding="utf-8")
            stdout = StringIO()
            with patch("ihav_web_visit_counter.providers.webtrafficchecker.lookup", return_value=result):
                with redirect_stdout(stdout):
                    exit_code = cli.main(["github.com", "--json", "--cache-dir", str(cache_root)])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "estimate")
        self.assertTrue(any("cache unavailable" in note.lower() for note in payload["notes"]))


if __name__ == "__main__":
    unittest.main()
