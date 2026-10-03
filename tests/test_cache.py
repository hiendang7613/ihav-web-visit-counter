from __future__ import annotations

import os
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins/ihav-web-visit-counter/core/ihav-web-visit-counter"
sys.path.insert(0, str(CORE))

from ihav_web_visit_counter.cache import Cache, default_cache_dir
from ihav_web_visit_counter.providers import webtrafficchecker


class CachePathTests(unittest.TestCase):
    def test_default_runtime_path_is_under_current_working_directory(self):
        with patch.dict(os.environ, {"IHAV_CACHE_DIR": ""}, clear=False):
            with patch("ihav_web_visit_counter.cache.Path.cwd", return_value=Path("/workspace/project")):
                self.assertEqual(
                    default_cache_dir(),
                    Path("/workspace/project/.ihav_space/ihav-web-visit-counter"),
                )

    def test_cache_directory_can_be_overridden(self):
        with patch.dict(os.environ, {"IHAV_CACHE_DIR": "/tmp/ihav-test-cache"}, clear=False):
            self.assertEqual(default_cache_dir(), Path("/tmp/ihav-test-cache"))

    def test_cache_reads_do_not_create_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "cache"
            cache = Cache(root)
            self.assertIsNone(cache.get_result("example.com"))
            self.assertIsNone(cache.get_daily_blob("tranco.zip"))
            self.assertFalse(root.exists())
            self.assertEqual(cache.warnings, [])

    def test_non_directory_cache_root_adds_warning_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "not-a-directory"
            root.write_text("file", encoding="utf-8")
            cache = Cache(root)
            self.assertIsNone(cache.get_result("example.com"))
            cached = cache.put_daily_blob("tranco.zip", b"fixture")
        self.assertEqual(cached.body, b"fixture")
        self.assertTrue(any("continuing without it" in warning for warning in cache.warnings))

    def test_cache_tolerates_small_future_mtime_skew_for_results_and_daily_lists(self):
        fixture = (Path(__file__).parent / "fixtures/webtrafficchecker/github.json").read_bytes()
        with patch.object(webtrafficchecker, "get_bytes", return_value=(200, fixture, {})):
            result = webtrafficchecker.lookup("github.com", "github.com")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache = Cache(root)
            cache.put_result(result)
            result_path = root / "results" / f"{sha256(b'github.com').hexdigest()}.json"
            result_mtime = result_path.stat().st_mtime
            with patch("ihav_web_visit_counter.cache.time.time", return_value=result_mtime - 0.02):
                self.assertIsNotNone(cache.get_result("github.com"))

            cache.put_daily_blob("daily.zip", b"fixture archive")
            archive_path = root / "sources" / "daily.zip"
            archive_mtime = archive_path.stat().st_mtime
            with patch("ihav_web_visit_counter.cache.time.time", return_value=archive_mtime - 0.02):
                cached_archive = cache.get_daily_blob("daily.zip")

        self.assertIsNotNone(cached_archive)
        self.assertEqual(cached_archive.body, b"fixture archive")


if __name__ == "__main__":
    unittest.main()
