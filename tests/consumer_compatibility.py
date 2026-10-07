"""Fixture-only checks against actual Leaderboards and Competitor plugin files."""

from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import os
import runpy
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--counter-plugin", type=Path, default=ROOT / "plugins/ihav-web-visit-counter")
parser.add_argument("--leaderboards-plugin", type=Path, required=True)
parser.add_argument("--competitor-plugin", type=Path, required=True)
args = parser.parse_args()

COUNTER = args.counter_plugin.resolve() / "core/ihav-web-visit-counter"
LEADER = args.leaderboards_plugin.resolve() / "core/ihav-leaderboards"
COMPETITOR = args.competitor_plugin.resolve() / "core/ihav-competitor-search"
for core, package in ((COUNTER, "ihav_web_visit_counter"), (LEADER, "ihav_leaderboards"),
                      (COMPETITOR, "ihav_competitor_search")):
    if not (core / package / "__init__.py").is_file():
        parser.error(f"Plugin package not found: {core / package}")
    sys.path.insert(0, str(core))

from ihav_web_visit_counter.errors import BlockedError
from ihav_web_visit_counter.models import result_from_dict
from ihav_web_visit_counter.providers import trafficlens, tranco, webtrafficchecker
from ihav_competitor_search.visits import CounterVisitStage, lookup_hosts


SCRIPT = COUNTER / "scripts/visits.py"
LEADER_SCRIPT = LEADER / "scripts/leaderboards.py"
FIXTURE = ROOT / "tests/fixtures/webtrafficchecker/github.json"
NETWORK_ERROR = "Consumer fixtures must not access the network"
NETWORK_GUARD = """import socket
def forbidden(*args, **kwargs):
    raise AssertionError("Consumer fixtures must not access the network")
socket.create_connection = forbidden
socket.getaddrinfo = forbidden
socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden
"""


def forbidden_network(*args, **kwargs):
    raise AssertionError(NETWORK_ERROR)


def run_counter(mode):
    with patch.object(webtrafficchecker, "get_bytes", return_value=(200, FIXTURE.read_bytes(), {})):
        original = webtrafficchecker.lookup("github.com", "github.com")
    value = original.to_dict()
    value["providers"] = []
    primary, secondary, rank = original, None, None
    if mode == "rounded_blocked":
        value.update(monthly_visits=None, monthly_visits_text="1.2K", analyzed_at=None,
                     scraped_at="2026-09-01", stale=True, history=None, history_source=None,
                     countries=None, countries_source=None,
                     source={"name": "TrafficLens", "url": "https://trafficlens.com/website/github.com"})
        primary, secondary = None, result_from_dict(value)
    elif mode == "rank":
        value.update(kind="rank_only", monthly_visits=None, monthly_visits_text=None,
                     analyzed_at=None, history=None, history_source=None, countries=None,
                     countries_source=None, rank={"value": 7, "date": "2026-09-30", "list": "Tranco daily top-1M list"},
                     source={"name": "Tranco", "url": "https://tranco-list.eu/"})
        primary, rank = None, result_from_dict(value)
    elif mode == "rounded_trillion":
        primary = None
    elif mode == "no_data":
        primary = None
    with tempfile.TemporaryDirectory() as cache, contextlib.ExitStack() as stack:
        output = io.StringIO()
        stack.enter_context(patch.object(sys, "argv", [str(SCRIPT), "github.com", "--json", "--cache-dir", cache]))
        stack.enter_context(contextlib.redirect_stdout(output))
        if mode in {"rounded_blocked", "blocked"}:
            primary_call = stack.enter_context(patch.object(webtrafficchecker, "lookup", side_effect=BlockedError(
                "fixture HTTP 403", source="webtrafficchecker", http_status=403)))
        else:
            primary_call = stack.enter_context(patch.object(webtrafficchecker, "lookup", return_value=primary))
        if mode == "rounded_trillion":
            stack.enter_context(patch.object(trafficlens, "get_bytes", return_value=(200, json.dumps({
                "domain": "github.com", "monthlyVisits": "1.2T",
                "scrapedAt": "2026-09-01T00:00:00Z", "source": "stale",
            }).encode("utf-8"), {})))
        else:
            stack.enter_context(patch.object(trafficlens, "lookup", return_value=secondary))
        stack.enter_context(patch.object(tranco, "lookup", return_value=rank))
        try:
            runpy.run_path(str(SCRIPT), run_name="__main__")
            code = 0
        except SystemExit as exc:
            code = int(exc.code or 0)
        if primary_call.call_count != 1:
            raise AssertionError(f"Primary provider dispatched {primary_call.call_count} times")
    expected_code = 4 if mode == "blocked" else 2 if mode == "no_data" else 0
    if code != expected_code:
        raise AssertionError(f"Fixture counter exit {code}: {output.getvalue()}")
    return code, json.loads(output.getvalue())


class ConsumerCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        stack = contextlib.ExitStack()
        cls.addClassCleanup(stack.close)
        for owner, name in ((socket, "create_connection"), (socket, "getaddrinfo"),
                            (socket.socket, "connect"), (socket.socket, "connect_ex")):
            stack.enter_context(patch.object(owner, name, side_effect=forbidden_network))
        guard = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        (guard / "sitecustomize.py").write_text(NETWORK_GUARD, encoding="utf-8")
        cls.environment = {**os.environ, "PYTHONPATH": str(guard), "PYTHONDONTWRITEBYTECODE": "1"}
        cls.primary = run_counter("primary")[1]
        cls.rounded = run_counter("rounded_blocked")[1]
        cls.rank = run_counter("rank")[1]
        cls.trillion = run_counter("rounded_trillion")[1]

    def command(self, arguments):
        return subprocess.run([sys.executable, *map(str, arguments)], capture_output=True,
                              text=True, encoding="utf-8", timeout=20, env=self.environment)

    def stage(self, directory, payload, code=0):
        shim = directory / "counter-fixture.py"
        shim.write_text("import json\nprint(json.dumps(" + repr(payload) + "))\nraise SystemExit(" + str(code) + ")\n",
                        encoding="utf-8")
        return CounterVisitStage(shim, directory, timeout=20)

    def test_child_network_is_disabled(self):
        result = self.command(["-c", "import socket; socket.create_connection(('127.0.0.1', 1))"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(NETWORK_ERROR, result.stderr)

    def test_counter_help(self):
        result = self.command([SCRIPT, "--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--json", result.stdout)

    def test_invalid_input_retains_usage_contract(self):
        result = self.command([SCRIPT, "https://", "--json"])
        self.assertEqual(result.returncode, 64, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["contract_version"], 2)
        self.assertEqual(payload["providers"], [])

    def test_no_data_comes_from_the_actual_counter_cli(self):
        code, payload = run_counter("no_data")
        self.assertEqual(code, 2)
        self.assertEqual(payload["contract_version"], 2)
        self.assertEqual(payload["error"]["code"], "no_data")
        self.assertEqual([p["outcome"] for p in payload["providers"]], ["no_data", "no_data", "no_data"])

    def test_primary_fixture_from_counter(self):
        self.assertEqual(self.primary["domain"], "github.com")
        self.assertEqual(self.primary["kind"], "estimate")
        self.assertEqual(self.primary["monthly_visits"], 486200000)
        self.assertEqual(self.primary["contract_version"], 2)
        self.assertIsNone(self.primary["period"])

    def test_blocked_then_rounded_fallback_is_explicit(self):
        self.assertIsNone(self.rounded["monthly_visits"])
        self.assertEqual(self.rounded["monthly_visits_text"], "1.2K")
        self.assertTrue(self.rounded["stale"])
        blocked = next(p for p in self.rounded["providers"] if p["name"] == "webtrafficchecker")
        self.assertEqual((blocked["outcome"], blocked["http_status"]), ("blocked", 403))

    def test_rank_never_becomes_a_visit_count(self):
        self.assertEqual(self.rank["kind"], "rank_only")
        self.assertIsNone(self.rank["monthly_visits"])
        self.assertIsNone(self.rank["monthly_visits_text"])
        self.assertEqual(self.rank["rank"]["value"], 7)

    def test_counter_rounded_trillion_preserves_provider_text(self):
        self.assertEqual(self.trillion["contract_version"], 2)
        self.assertEqual(self.trillion["kind"], "estimate")
        self.assertIsNone(self.trillion["monthly_visits"])
        self.assertEqual(self.trillion["monthly_visits_text"], "1.2T")
        self.assertIsNone(self.trillion["period"])
        self.assertEqual(self.trillion["source"]["name"], "TrafficLens")
        self.assertEqual(self.trillion["scraped_at"], "2026-09-01T00:00:00Z")
        self.assertTrue(self.trillion["stale"])
        outcome = next(p for p in self.trillion["providers"] if p["name"] == "trafficlens")
        self.assertEqual((outcome["outcome"], outcome["http_status"]), ("ok", 200))

    def test_leaderboards_weighs_rounded_null_and_labels_rank_floor(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "visits").mkdir()
            (run / "boards.json").write_text(json.dumps({"boards": [
                {"slug": "a", "domain": "github.com", "status": "live"},
                {"slug": "b", "domain": "github.com", "status": "live"},
                {"slug": "c", "domain": "rank.invalid", "status": "live"}]}), encoding="utf-8")
            (run / "visits/known.json").write_text(json.dumps(self.rounded), encoding="utf-8")
            rank = copy.deepcopy(self.rank)
            rank["domain"] = "rank.invalid"
            (run / "visits/rank.json").write_text(json.dumps(rank), encoding="utf-8")
            result = self.command([LEADER_SCRIPT, "weigh", run])
            self.assertEqual(result.returncode, 0, result.stderr)
            entries = {e["slug"]: e for e in json.loads((run / "weights.json").read_text())["boards"]}
            self.assertEqual(entries["a"]["mass"], 600)
            self.assertEqual(entries["b"]["mass"], 600)
            for slug in ("a", "b"):
                with self.subTest(slug=slug):
                    self.assertIsNone(entries[slug]["monthly_visits"])
                    self.assertEqual(entries[slug]["monthly_visits_text"], "1.2K")
            self.assertEqual(entries["c"]["mass"], 1200)
            self.assertIsNone(entries["c"]["monthly_visits"])
            self.assertEqual(entries["c"]["weight_basis"], "floor+domain_split(1)")

    def test_leaderboards_rank_only_stops_without_equal_weights(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "visits").mkdir()
            (run / "boards.json").write_text(json.dumps({"boards": [
                {"slug": "a", "domain": "github.com", "status": "live"}]}), encoding="utf-8")
            (run / "visits/rank.json").write_text(json.dumps(self.rank), encoding="utf-8")
            result = self.command([LEADER_SCRIPT, "weigh", run])
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertTrue((run / "diagnostic.json").is_file())
            self.assertFalse((run / "weights.json").exists())

    def test_leaderboards_022_trillion_policy_floor_or_diagnostic(self):
        for mixed in (False, True):
            with self.subTest(mixed=mixed), tempfile.TemporaryDirectory() as temporary:
                run = Path(temporary)
                (run / "visits").mkdir()
                boards = [{"slug": "trillion", "domain": "github.com", "status": "live"}]
                (run / "visits/trillion.json").write_text(json.dumps(self.trillion), encoding="utf-8")
                if mixed:
                    known = copy.deepcopy(self.primary)
                    known["domain"] = "known.invalid"
                    boards.append({"slug": "known", "domain": "known.invalid", "status": "live"})
                    (run / "visits/known.json").write_text(json.dumps(known), encoding="utf-8")
                (run / "boards.json").write_text(json.dumps({"boards": boards}), encoding="utf-8")
                result = self.command([LEADER_SCRIPT, "weigh", run])
                if mixed:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    weights = json.loads((run / "weights.json").read_text())
                    entries = {e["slug"]: e for e in weights["boards"]}
                    self.assertEqual(weights["floor_domains"], ["github.com"])
                    self.assertEqual(entries["trillion"]["mass"], self.primary["monthly_visits"])
                    self.assertEqual(entries["trillion"]["weight_basis"], "floor+domain_split(1)")
                    self.assertIsNone(entries["trillion"]["monthly_visits"])
                    self.assertEqual(entries["trillion"]["monthly_visits_text"], "1.2T")
                else:
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertTrue((run / "diagnostic.json").is_file())
                    self.assertFalse((run / "weights.json").exists())

    def test_competitor_preserves_payload_and_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = self.stage(Path(temporary), self.rounded)
            with patch.dict(os.environ, self.environment):
                record = stage.lookup("github.com")
            self.assertEqual(record["exit_code"], 0)
            self.assertEqual(record["result"], self.rounded)
            self.assertTrue(record["primary_blocked"])

    def test_competitor_preserves_rounded_trillion_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = self.stage(Path(temporary), self.trillion)
            with patch.dict(os.environ, self.environment):
                record = stage.lookup("github.com")
            self.assertEqual(record["exit_code"], 0)
            self.assertEqual(record["result"], self.trillion)

    def test_competitor_source_block_prevents_more_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = self.stage(root, self.rounded)
            stage.lookup = Mock(wraps=stage.lookup)
            table = {"rows": [{"lookup_host": "github.com"}, {"lookup_host": "other.invalid"}]}
            with patch.dict(os.environ, self.environment):
                first = lookup_hosts(table, root, stage)
                second = lookup_hosts(table, root, stage)
            self.assertEqual(stage.lookup.call_count, 1)
            self.assertEqual(first["other.invalid"]["reason"], "blocked")
            self.assertEqual(second["github.com"]["result"], self.rounded)

    def test_competitor_retains_terminal_exit4_without_retry(self):
        code, payload = run_counter("blocked")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = self.stage(root, payload, code)
            stage.lookup = Mock(wraps=stage.lookup)
            table = {"rows": [{"lookup_host": "github.com"}, {"lookup_host": "other.invalid"}]}
            with patch.dict(os.environ, self.environment):
                first = lookup_hosts(table, root, stage)
                lookup_hosts(table, root, stage)
            self.assertEqual(stage.lookup.call_count, 1)
            self.assertEqual(first["github.com"]["exit_code"], 4)
            self.assertEqual(first["other.invalid"]["reason"], "blocked")

    def test_competitor_no_data_does_not_block_another_host(self):
        code, payload = run_counter("no_data")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = self.stage(root, payload, code)
            stage.lookup = Mock(wraps=stage.lookup)
            table = {"rows": [{"lookup_host": "github.com"}, {"lookup_host": "other.invalid"}]}
            with patch.dict(os.environ, self.environment):
                first = lookup_hosts(table, root, stage)
                lookup_hosts(table, root, stage)
            self.assertEqual(stage.lookup.call_count, 2)
            for host in ("github.com", "other.invalid"):
                with self.subTest(host=host):
                    self.assertEqual(first[host]["exit_code"], 2)
                    self.assertFalse(first[host]["primary_blocked"])


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
