"""TrafficLens's keyless public Worker response when it contains a visits value."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from ..errors import ProviderError
from ..http import get_bytes
from ..models import VisitResult


BASE_URL = "https://traffic-lens-api.admin-d10.workers.dev/api/analyze/"
DISPLAY_URL = "https://trafficlens.io/"
SOURCE_NAME = "TrafficLens"
_VISIT_STRING = re.compile(r"^\d+(?:\.\d+)?[KMBT]?$", re.IGNORECASE)


def _visit_value(value: object) -> int | str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if not isinstance(value, str) or not _VISIT_STRING.fullmatch(value):
        return None
    number = value[:-1] if value[-1:].upper() in {"K", "M", "B", "T"} else value
    try:
        positive = Decimal(number) > 0
    except InvalidOperation:
        return None
    return value if positive else None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        number = int(value)
        return number if number > 0 else None
    return None


def _scraped_at(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return value


def _countries(value: object) -> list[dict[str, object]] | None:
    if not isinstance(value, list):
        return None
    countries = []
    for row in value:
        if not isinstance(row, dict):
            continue
        country = row.get("country")
        percentage = row.get("percentage")
        if not isinstance(country, str) or isinstance(percentage, bool):
            continue
        try:
            percentage_value = float(percentage)
        except (TypeError, ValueError, OverflowError):
            continue
        if not math.isfinite(percentage_value) or not 0 <= percentage_value <= 100:
            continue
        countries.append({"country": country, "share": round(percentage_value / 100.0, 4)})
    return countries or None


def lookup(domain: str, original_input: str, cache=None) -> VisitResult | None:
    url = f"{BASE_URL}{domain}"
    status, body, _headers = get_bytes(url, "application/json")
    if status == 404:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderError("TrafficLens returned invalid JSON; no retry was made.", SOURCE_NAME) from exc
    if not isinstance(payload, dict):
        raise ProviderError("TrafficLens returned an unexpected JSON shape; no retry was made.", SOURCE_NAME)

    payload_domain = payload.get("domain")
    if not isinstance(payload_domain, str):
        return None
    returned_domain = payload_domain.strip().lower().removeprefix("www.")
    if returned_domain != domain.lower().removeprefix("www."):
        return None
    if str(payload.get("dataKind", "")).strip().lower() == "ranking":
        return None

    visits = _visit_value(payload.get("monthlyVisits"))
    scraped_at = _scraped_at(payload.get("scrapedAt"))
    if visits is None or scraped_at is None:
        return None
    visits_text = visits if isinstance(visits, str) else f"{visits:,}"

    stale = payload.get("source") == "stale"
    rank_value = _positive_int(payload.get("globalRank"))
    rank = None
    if rank_value is not None:
        rank = {
            "value": rank_value,
            "list": "TrafficLens global rank",
            "date": scraped_at[:10],
        }
    countries = _countries(payload.get("topCountries"))
    source = {
        "name": SOURCE_NAME,
        "layer": "fallback",
        "method": "provider-reported",
        "url": DISPLAY_URL,
        "api_url": url,
        "scraped_at": scraped_at,
        "upstream_status": payload.get("source"),
    }
    return VisitResult(
        input=original_input,
        domain=domain,
        kind="estimate",
        monthly_visits=None,
        monthly_visits_text=visits_text,
        period=None,
        analyzed_at=None,
        range=None,
        confidence=None,
        rank=rank,
        history=None,
        history_source=None,
        countries=countries,
        countries_source={"name": SOURCE_NAME, "layer": "fallback", "scraped_at": scraped_at} if countries else None,
        source=source,
        calibration=None,
        fetched_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        cached=False,
        notes=[
            "TrafficLens is a third-party estimate, not the website owner's analytics; no independently measured error interval is available.",
            "TrafficLens names SimilarWeb among its upstreams; upstream reuse terms may also apply.",
        ],
        scraped_at=scraped_at,
        stale=stale,
    )
