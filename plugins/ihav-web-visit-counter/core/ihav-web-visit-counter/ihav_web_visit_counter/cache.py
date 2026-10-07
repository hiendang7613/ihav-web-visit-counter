"""Small atomic JSON and daily-list cache under the configured project data directory."""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from .errors import CacheError
from .models import VisitResult, result_from_dict


RESULT_TTL_SECONDS = 24 * 60 * 60
LIST_TTL_SECONDS = 24 * 60 * 60
CLOCK_SKEW_TOLERANCE_SECONDS = 1


@dataclass
class CachedBytes:
    body: bytes
    stored_at: str


def default_cache_dir() -> Path:
    override = os.environ.get("IHAV_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    return Path.cwd() / ".ihav_space" / "ihav-web-visit-counter"


class Cache:
    def __init__(self, root: Path):
        self.root = root.expanduser()
        self.warnings: list[str] = []

    def _warn(self, path: Path, operation: str, detail: str = "") -> None:
        message = f"Local cache unavailable at {path} ({operation}); continuing without it."
        if detail:
            message = f"{message} {detail}"
        if message not in self.warnings:
            self.warnings.append(message)

    def _ensure(self, folder: str) -> Path:
        path = self.root / folder
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CacheError(f"Cannot create cache directory {path}: {exc}") from exc
        return path

    def _fresh(self, path: Path, ttl: int) -> bool:
        try:
            age = time.time() - path.stat().st_mtime
        except FileNotFoundError:
            return False
        except OSError as exc:
            self._warn(path, "read", str(exc))
            return False
        # Windows can report a file timestamp slightly ahead of time.time() on
        # older Python versions. Treat that small clock skew as a fresh entry.
        return -CLOCK_SKEW_TOLERANCE_SECONDS <= age < ttl

    @staticmethod
    def _atomic_write(path: Path, body: bytes) -> None:
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".tmp-", delete=False) as temporary:
                temporary_name = temporary.name
                temporary.write(body)
                temporary.flush()
            os.replace(temporary_name, path)
        except OSError as exc:
            if temporary_name:
                try:
                    os.unlink(temporary_name)
                except OSError:
                    pass
            raise CacheError(f"Cannot write cache file {path}: {exc}") from exc

    def get_result(self, domain: str) -> VisitResult | None:
        key = sha256(domain.encode("utf-8")).hexdigest()
        path = self.root / "results" / f"{key}.json"
        if not self._fresh(path, RESULT_TTL_SECONDS):
            return None
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            result = result_from_dict(envelope["result"])
            if result.domain != domain:
                raise ValueError("Cached result belongs to a different domain.")
        except OSError as exc:
            self._warn(path, "read", str(exc))
            return None
        except (AttributeError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self._warn(path, "validate", str(exc))
            return None
        result.cached = True
        return result

    def put_result(self, result: VisitResult) -> None:
        key = sha256(result.domain.encode("utf-8")).hexdigest()
        path = self.root / "results" / f"{key}.json"
        envelope = {
            "stored_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "result": result.to_dict(),
        }
        try:
            self._ensure("results")
            self._atomic_write(path, json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        except CacheError as exc:
            self._warn(path, "write", exc.message)

    def get_daily_blob(self, filename: str) -> CachedBytes | None:
        path = self.root / "sources" / filename
        if not self._fresh(path, LIST_TTL_SECONDS):
            return None
        try:
            stored_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")
            return CachedBytes(path.read_bytes(), stored_at)
        except OSError as exc:
            self._warn(path, "read", str(exc))
            return None

    def put_daily_blob(self, filename: str, body: bytes) -> CachedBytes:
        path = self.root / "sources" / filename
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            self._ensure("sources")
            self._atomic_write(path, body)
            stored_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")
        except (CacheError, OSError) as exc:
            self._warn(path, "write", getattr(exc, "message", str(exc)))
            stored_at = now
        return CachedBytes(body, stored_at)
