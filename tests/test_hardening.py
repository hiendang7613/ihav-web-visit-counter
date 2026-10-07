from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from hashlib import sha256
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
import zipfile


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins/ihav-web-visit-counter/core/ihav-web-visit-counter"
sys.path.insert(0, str(CORE))

from ihav_web_visit_counter import cli, http
from ihav_web_visit_counter.cache import Cache
from ihav_web_visit_counter.errors import BlockedError, ProviderError
from ihav_web_visit_counter.models import result_from_dict
from ihav_web_visit_counter.numeric import json_integer
from ihav_web_visit_counter.providers import trafficlens, tranco, webtrafficchecker
from ihav_web_visit_counter.service import lookup


class CacheIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.body = (ROOT / "tests/fixtures/webtrafficchecker/github.json").read_bytes()
        with patch.object(webtrafficchecker, "get_bytes", return_value=(200, self.body, {})):
            self.result = webtrafficchecker.lookup("github.com", "github.com")

    def write_cache(self, root, value):
        path = root / "results" / f"{sha256(b'github.com').hexdigest()}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"result": value}), encoding="utf-8")

    def test_cached_result_must_belong_to_the_requested_domain(self):
        value = self.result.to_dict()
        value["domain"] = "python.org"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_cache(root, value)
            cache = Cache(root)
            self.assertIsNone(cache.get_result("github.com"))
            self.assertTrue(cache.warnings)

    def test_corrupt_cache_is_refetched_through_the_cli(self):
        mutations = {
            "negative_visits": {"monthly_visits": -1},
            "empty_display": {"monthly_visits_text": ""},
            "history_text": {"history": [{"date": "2026-09-11", "visits": "broken"}]},
            "history_boolean": {"history": [{"date": "2026-09-11", "visits": True}]},
            "country_text": {"countries": [{"country": "US", "share": "broken"}]},
            "country_nonfinite": {"countries": [{"country": "US", "share": float("nan")}]},
            "country_out_of_range": {"countries": [{"country": "US", "share": 1.5}]},
            "rank_text": {"rank": {"value": "broken", "list": "fixture", "date": "2026-09-11"}},
            "missing_source_url": {"source": {"name": "WebTrafficChecker"}},
            "missing_attribution": {"source": []},
            "notes_text": {"notes": "broken"},
            "timestamp_number": {"analyzed_at": 42},
            "missing_fetched_at": {"fetched_at": None},
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                value = self.result.to_dict()
                value.update(mutation)
                self.write_cache(root, value)
                out = StringIO()
                with patch.object(webtrafficchecker, "get_bytes", return_value=(200, self.body, {})) as fetch:
                    with patch.object(trafficlens, "lookup", side_effect=AssertionError("no fallback needed")):
                        with patch.object(tranco, "lookup", side_effect=AssertionError("no fallback needed")):
                            with redirect_stdout(out):
                                code = cli.main(["github.com", "--cache-dir", str(root)])
                self.assertEqual(code, 0)
                fetch.assert_called_once()
                self.assertIn("~486,200,000 estimated monthly visits", out.getvalue())
                self.assertIn("continuing without it", out.getvalue())
                restored = Cache(root).get_result("github.com")
                self.assertEqual(restored.monthly_visits, 486200000)

    def test_cache_warnings_are_not_stored_with_the_refreshed_result(self):
        value = self.result.to_dict()
        value["monthly_visits"] = -1
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_cache(root, value)
            with patch.object(webtrafficchecker, "get_bytes", return_value=(200, self.body, {})) as fetch:
                first = lookup("github.com", root)
                second = lookup("github.com", root)
        fetch.assert_called_once()
        self.assertTrue(any("continuing without it" in note for note in first.notes))
        self.assertTrue(second.cached)
        self.assertFalse(any("continuing without it" in note for note in second.notes), second.notes)

    def test_valid_result_and_legacy_cache_shapes_remain_readable(self):
        value = self.result.to_dict()
        restored = result_from_dict(value)
        self.assertEqual(restored.to_dict(), value)
        for field in ("scraped_at", "stale", "monthly_visits_text", "providers"):
            value.pop(field)
        value["contract_version"] = 1
        restored = result_from_dict(value)
        self.assertEqual(restored.monthly_visits, 486200000)
        self.assertEqual(restored.monthly_visits_text, "486,200,000")


class HTTPResourceTests(unittest.TestCase):
    def test_http_error_responses_are_closed_on_every_return_or_raise(self):
        cases = (
            (401, b"refused", BlockedError),
            (403, b"refused", BlockedError),
            (429, b"rate limited", BlockedError),
            (404, b"not found", None),
            (500, b"server error", ProviderError),
            (503, b"<html>Verify you are human</html>", BlockedError),
            (302, b"redirect", ProviderError),
        )
        for status, body, error_type in cases:
            with self.subTest(status=status):
                stream = BytesIO(body)
                headers = {"Location": "https://other.example/"} if status == 302 else {}
                error = HTTPError("https://provider.example/", status, "fixture", headers, stream)
                with patch.object(http._OPENER, "open", side_effect=error) as fetch:
                    if error_type is None:
                        actual_status, actual_body, _headers = http.get_bytes("https://provider.example/", "application/json")
                        self.assertEqual((actual_status, actual_body), (404, body))
                    else:
                        with self.assertRaises(error_type) as raised:
                            http.get_bytes("https://provider.example/", "application/json")
                        self.assertEqual(raised.exception.http_status, status)
                fetch.assert_called_once()
                self.assertTrue(stream.closed, "The retained HTTPError must not retain an open response body")


class MalformedNumberTests(unittest.TestCase):
    def test_json_integer_conversion_preserves_zero_and_signed_values(self):
        self.assertEqual(json.loads("[0, -0, 42, -42]", parse_int=json_integer), [0, 0, 42, -42])
        oversized = "9" * 4301
        self.assertEqual(json.loads("[" + oversized + ", -" + oversized + "]", parse_int=json_integer), [None, None])

    def test_oversized_json_integer_primary_continues_to_trafficlens(self):
        primary = json.loads((ROOT / "tests/fixtures/webtrafficchecker/github.json").read_text())
        primary["traffic"]["monthlyVisits"] = "__oversized_integer__"
        body = json.dumps(primary).replace('"__oversized_integer__"', "9" * 4301).encode()
        fallback = (ROOT / "tests/fixtures/trafficlens/stale-github.json").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(webtrafficchecker, "get_bytes", return_value=(200, body, {})) as first:
                with patch.object(trafficlens, "get_bytes", return_value=(200, fallback, {})) as second:
                    with patch.object(tranco, "lookup", side_effect=AssertionError("usable fallback ends the chain")):
                        output = StringIO()
                        with redirect_stdout(output):
                            code = cli.main(["github.com", "--json", "--cache-dir", temporary])
        self.assertEqual(code, 0, output.getvalue())
        first.assert_called_once()
        second.assert_called_once()
        result = json.loads(output.getvalue())
        self.assertEqual(result["source"]["name"], "TrafficLens")
        self.assertEqual(result["monthly_visits_text"], "631.0M")
        self.assertIsNone(result["monthly_visits"])
        self.assertEqual([p["outcome"] for p in result["providers"]], ["no_data", "ok", "skipped"])

    def test_oversized_json_integer_trafficlens_continues_to_tranco(self):
        fallback = json.loads((ROOT / "tests/fixtures/trafficlens/stale-github.json").read_text())
        fallback["monthlyVisits"] = "__oversized_integer__"
        body = json.dumps(fallback).replace('"__oversized_integer__"', "9" * 4301).encode()
        archive = (ROOT / "tests/fixtures/tranco/top-1m.csv.zip").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(webtrafficchecker, "get_bytes", return_value=(404, b"not found", {})) as first:
                with patch.object(trafficlens, "get_bytes", return_value=(200, body, {})) as second:
                    with patch.object(tranco, "get_bytes", return_value=(200, archive, {})) as third:
                        output = StringIO()
                        with redirect_stdout(output):
                            code = cli.main(["github.com", "--json", "--cache-dir", temporary])
        self.assertEqual(code, 0, output.getvalue())
        first.assert_called_once()
        second.assert_called_once()
        third.assert_called_once()
        result = json.loads(output.getvalue())
        self.assertEqual(result["kind"], "rank_only")
        self.assertEqual(result["rank"]["value"], 20)
        self.assertIsNone(result["monthly_visits"])
        self.assertIsNone(result["monthly_visits_text"])
        self.assertEqual([p["outcome"] for p in result["providers"]], ["no_data", "no_data", "ok"])

    def test_whole_number_floats_count_only_within_exact_integer_range(self):
        self.assertEqual(webtrafficchecker._as_positive_int(float(2**53)), 2**53)
        for value in (float(2**53 + 2), 1e308, float("inf"), float("nan")):
            with self.subTest(value=value):
                self.assertIsNone(webtrafficchecker._as_positive_int(value))

    def test_huge_float_primary_visits_continue_to_trafficlens(self):
        primary = json.loads((ROOT / "tests/fixtures/webtrafficchecker/github.json").read_text())
        primary["traffic"]["monthlyVisits"] = 1e308
        fallback = (ROOT / "tests/fixtures/trafficlens/stale-github.json").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(webtrafficchecker, "get_bytes", return_value=(200, json.dumps(primary).encode(), {})) as first:
                with patch.object(trafficlens, "get_bytes", return_value=(200, fallback, {})) as second:
                    with patch.object(tranco, "lookup", side_effect=AssertionError("usable fallback ends the chain")):
                        result = lookup("github.com", Path(temporary))
        first.assert_called_once()
        second.assert_called_once()
        self.assertEqual(result.source["name"], "TrafficLens")
        self.assertEqual(result.monthly_visits_text, "631.0M")
        self.assertIsNone(result.monthly_visits)

    def test_superscript_digits_do_not_interrupt_the_provider_chain(self):
        primary = json.loads((ROOT / "tests/fixtures/webtrafficchecker/github.json").read_text())
        primary["traffic"]["monthlyVisits"] = "²"
        fallback = json.loads((ROOT / "tests/fixtures/trafficlens/stale-github.json").read_text())
        fallback["globalRank"] = "²"
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(webtrafficchecker, "get_bytes", return_value=(200, json.dumps(primary).encode(), {})) as first:
                with patch.object(trafficlens, "get_bytes", return_value=(200, json.dumps(fallback).encode(), {})) as second:
                    with patch.object(tranco, "lookup", side_effect=AssertionError("usable estimate ends the chain")):
                        result = lookup("github.com", Path(temporary))
        first.assert_called_once()
        second.assert_called_once()
        self.assertEqual(result.source["name"], "TrafficLens")
        self.assertEqual(result.monthly_visits_text, "631.0M")
        self.assertIsNone(result.monthly_visits)
        self.assertIsNone(result.rank)

    def test_oversized_decimal_strings_do_not_interrupt_the_provider_chain(self):
        primary = json.loads((ROOT / "tests/fixtures/webtrafficchecker/github.json").read_text())
        primary["traffic"]["monthlyVisits"] = "9" * 5000
        fallback = json.loads((ROOT / "tests/fixtures/trafficlens/stale-github.json").read_text())
        fallback["globalRank"] = "9" * 5000
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(webtrafficchecker, "get_bytes", return_value=(200, json.dumps(primary).encode(), {})) as first:
                with patch.object(trafficlens, "get_bytes", return_value=(200, json.dumps(fallback).encode(), {})) as second:
                    with patch.object(tranco, "lookup", side_effect=AssertionError("usable estimate ends the chain")):
                        result = lookup("github.com", Path(temporary))
        first.assert_called_once()
        second.assert_called_once()
        self.assertEqual(result.source["name"], "TrafficLens")
        self.assertEqual(result.monthly_visits_text, "631.0M")
        self.assertIsNone(result.monthly_visits)
        self.assertIsNone(result.rank)

    def test_valid_numeric_forms_keep_each_provider_contract(self):
        for parse in (webtrafficchecker._as_positive_int, trafficlens._positive_int):
            for value in (20, "20", "٢٠"):
                with self.subTest(parser=parse.__name__, value=value):
                    self.assertEqual(parse(value), 20)
            for value in (True, 0, "0", "²", "-1", "1.5"):
                with self.subTest(parser=parse.__name__, value=value):
                    self.assertIsNone(parse(value))
        self.assertEqual(webtrafficchecker._as_positive_int(20.0), 20)
        self.assertIsNone(trafficlens._positive_int(20.0))


class DailyListIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.good = (ROOT / "tests/fixtures/tranco/top-1m.csv.zip").read_bytes()

    def invalid_archives(self):
        archive = BytesIO()
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("top-1m.csv", b"temporarily unavailable\n")
        return (b"temporarily unavailable\n", archive.getvalue())

    def test_invalid_download_is_not_stored_as_a_fresh_daily_list(self):
        for body in self.invalid_archives():
            with self.subTest(zipped=body.startswith(b"PK")), tempfile.TemporaryDirectory() as temporary:
                cache = Cache(Path(temporary))
                with patch.object(tranco, "get_bytes", return_value=(200, body, {})) as fetch:
                    with self.assertRaises(ProviderError):
                        tranco.lookup("github.com", "github.com", cache)
                fetch.assert_called_once()
                self.assertIsNone(cache.get_daily_blob(tranco.LIST_CACHE_NAME))

    def test_bad_download_does_not_poison_a_later_lookup_for_another_domain(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Cache(Path(temporary))
            with patch.object(tranco, "get_bytes", side_effect=[(200, b"temporarily unavailable", {}), (200, self.good, {})]) as fetch:
                with self.assertRaises(ProviderError):
                    tranco.lookup("github.com", "github.com", cache)
                result = tranco.lookup("python.org", "python.org", cache)
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(result.rank["value"], 640)
            self.assertIsNone(result.monthly_visits)

    def test_corrupt_existing_list_uses_one_download_and_keeps_rank_only_semantics(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Cache(Path(temporary))
            cache.put_daily_blob(tranco.LIST_CACHE_NAME, b"temporarily unavailable")
            with patch.object(tranco, "get_bytes", return_value=(200, self.good, {})) as fetch:
                result = tranco.lookup("github.com", "github.com", cache)
            fetch.assert_called_once()
            self.assertEqual(result.kind, "rank_only")
            self.assertEqual(result.rank["value"], 20)
            self.assertIsNone(result.monthly_visits)
            self.assertEqual(cache.get_daily_blob(tranco.LIST_CACHE_NAME).body, self.good)

    def test_malformed_rank_digits_do_not_hide_a_later_valid_row(self):
        body = "²,other.example\n20,github.com\n".encode()
        self.assertEqual(tranco.rank_in_list(body, "github.com"), 20)

    def test_oversized_cached_rank_uses_one_replacement_download(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Cache(Path(temporary))
            cache.put_daily_blob(tranco.LIST_CACHE_NAME, ("9" * 5000 + ",github.com\n").encode())
            with patch.object(tranco, "get_bytes", return_value=(200, self.good, {})) as fetch:
                result = tranco.lookup("github.com", "github.com", cache)
            fetch.assert_called_once()
            self.assertEqual(result.rank["value"], 20)
            self.assertIsNone(result.monthly_visits)
            self.assertEqual(cache.get_daily_blob(tranco.LIST_CACHE_NAME).body, self.good)

    def test_zero_rank_and_empty_domain_downloads_are_not_stored(self):
        for body in (b"0,github.com\n", b"0,other.example\n", b"1,\n", b"1,www.\n"):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as temporary:
                cache = Cache(Path(temporary))
                with patch.object(tranco, "get_bytes", return_value=(200, body, {})) as fetch:
                    with self.assertRaises(ProviderError):
                        tranco.lookup("github.com", "github.com", cache)
                fetch.assert_called_once()
                self.assertIsNone(cache.get_daily_blob(tranco.LIST_CACHE_NAME))

    def test_zero_rank_and_empty_domain_cached_lists_are_replaced_once(self):
        for body in (b"0,github.com\n", b"0,other.example\n", b"1,\n", b"1,www.\n"):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as temporary:
                cache = Cache(Path(temporary))
                cache.put_daily_blob(tranco.LIST_CACHE_NAME, body)
                with patch.object(tranco, "get_bytes", return_value=(200, self.good, {})) as fetch:
                    result = tranco.lookup("github.com", "github.com", cache)
                fetch.assert_called_once()
                self.assertEqual(result.rank["value"], 20)
                self.assertTrue(any("invalid cached Tranco list" in warning for warning in cache.warnings))

    def test_invalid_rank_rows_do_not_hide_a_later_valid_target(self):
        bodies = (b"0,github.com\n20,github.com\n", b"1,\n20,github.com\n",
                  ("9" * 5000 + ",other.example\n20,github.com\n").encode(),
                  "github.com,٢٠\n".encode())
        for body in bodies:
            with self.subTest(prefix=body[:30]):
                self.assertEqual(tranco.rank_in_list(body, "github.com"), 20)


if __name__ == "__main__":
    unittest.main()
