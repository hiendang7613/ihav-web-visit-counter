"""Local rank lookup against one cached download of Tranco's daily top-1M list."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime, timezone

from ..cache import Cache, CachedBytes
from ..errors import ProviderError
from ..http import get_bytes
from ..models import VisitResult


LIST_URL = "https://tranco-list.eu/top-1m.csv.zip"
LIST_CACHE_NAME = "tranco-top-1m.csv.zip"
SOURCE_NAME = "Tranco"
MAX_UNZIPPED_BYTES = 100 * 1024 * 1024


def _csv_bytes(body: bytes) -> bytes:
    if body.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
                if not names:
                    raise ProviderError("Tranco's list archive contains no CSV file.", SOURCE_NAME)
                with archive.open(names[0]) as source:
                    csv_body = source.read(MAX_UNZIPPED_BYTES + 1)
        except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
            raise ProviderError("Tranco returned an invalid list archive.", SOURCE_NAME) from exc
        if len(csv_body) > MAX_UNZIPPED_BYTES:
            raise ProviderError("Tranco's uncompressed list exceeded the 100 MiB safety limit.", SOURCE_NAME)
        return csv_body
    return body


def rank_in_list(body: bytes, domain: str) -> int | None:
    csv_body = _csv_bytes(body)
    try:
        text = io.TextIOWrapper(io.BytesIO(csv_body), encoding="utf-8-sig", errors="strict")
        reader = csv.reader(text)
        saw_row = False
        for row in reader:
            if len(row) < 2:
                continue
            first, second = row[0].strip(), row[1].strip()
            if first.lower() in {"rank", "position"} or second.lower() in {"domain", "host"}:
                continue
            if first.isdigit():
                rank, listed_domain = int(first), second
            elif second.isdigit():
                listed_domain, rank = first, int(second)
            else:
                continue
            saw_row = True
            normalized_listed = listed_domain.lower().rstrip(".")
            if normalized_listed.startswith("www."):
                normalized_listed = normalized_listed[4:]
            if normalized_listed == domain:
                return rank if rank > 0 else None
        if not saw_row:
            raise ProviderError("Tranco's downloaded list did not contain parseable rank rows.", SOURCE_NAME)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ProviderError("Tranco's downloaded list was not valid CSV.", SOURCE_NAME) from exc
    return None


def _get_daily_list(cache: Cache) -> CachedBytes:
    cached = cache.get_daily_blob(LIST_CACHE_NAME)
    if cached is not None:
        return cached
    status, body, _headers = get_bytes(
        LIST_URL,
        "application/zip, text/csv;q=0.9, */*;q=0.1",
        redirect_host="tranco-list.eu",
    )
    if status != 200:
        raise ProviderError(f"Tranco returned HTTP {status} for its daily list.", SOURCE_NAME)
    # Parse before storing so a corrupt or unexpected download is never retained as a fresh list.
    _csv_bytes(body)
    return cache.put_daily_blob(LIST_CACHE_NAME, body)


def lookup(domain: str, original_input: str, cache: Cache) -> VisitResult | None:
    daily_list = _get_daily_list(cache)
    rank = rank_in_list(daily_list.body, domain)
    if rank is None:
        return None
    retrieved_date = daily_list.stored_at[:10]
    return VisitResult(
        input=original_input,
        domain=domain,
        kind="rank_only",
        monthly_visits=None,
        period=None,
        analyzed_at=None,
        range=None,
        confidence=None,
        rank={
            "value": rank,
            "list": "Tranco daily top-1M list",
            "date": retrieved_date,
            "date_basis": "retrieved; the latest-list URL does not expose its publication date in the downloaded CSV",
        },
        history=None,
        history_source=None,
        countries=None,
        countries_source=None,
        source={
            "name": SOURCE_NAME,
            "layer": "fallback",
            "method": "daily-public-rank-list",
            "url": LIST_URL,
            "retrieved_at": daily_list.stored_at,
        },
        calibration=None,
        fetched_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        cached=False,
        notes=[
            "Tranco is a popularity rank, not a monthly visit count.",
            "Monthly visits are unknown; no calibrated rank-to-visits estimate is available.",
            "Tranco's composite list includes upstream signals with different licenses; this plugin downloads the list locally and does not bundle it.",
        ],
    )
