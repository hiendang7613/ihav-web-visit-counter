"""Run the installed-style entry point with a fixture while CI captures stdout."""

from __future__ import annotations

import runpy
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins/ihav-web-visit-counter/core/ihav-web-visit-counter"
SCRIPT = CORE / "scripts/visits.py"
sys.path.insert(0, str(CORE))

from ihav_web_visit_counter.providers import trafficlens, tranco, webtrafficchecker


def main() -> int:
    fixture = (ROOT / "tests/fixtures/webtrafficchecker/github.json").read_bytes()
    with patch.object(webtrafficchecker, "get_bytes", return_value=(200, fixture, {})):
        result = webtrafficchecker.lookup("github.com", "github.com")

    original_argv = sys.argv
    try:
        with tempfile.TemporaryDirectory() as temporary:
            sys.argv = [str(SCRIPT), "github.com", "--cache-dir", temporary]
            with patch.object(webtrafficchecker, "lookup", return_value=result):
                with patch.object(trafficlens, "lookup", return_value=None):
                    with patch.object(tranco, "lookup", return_value=None):
                        try:
                            runpy.run_path(str(SCRIPT), run_name="__main__")
                        except SystemExit as exc:
                            return int(exc.code or 0)
    finally:
        sys.argv = original_argv
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
