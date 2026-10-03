"""WebTrafficChecker's public, provider-modelled traffic estimate endpoint."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode

from ..errors import ProviderError
from ..http import get_bytes
from ..models import ProviderTrace, VisitResult


BASE_URL = "https://webtrafficchecker.com/api/traffic"
DISPLAY_URL = "https://webtrafficchecker.com/traffic/"
SOURCE_NAME = "WebTrafficChecker"
PROVIDER_ID = "webtrafficchecker"


def _as_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        number = value
    elif isinstance(value, float) and value.is_integer():
        number = int(value)
    elif isinstance(value, str) and value.isdigit():
        number = int(value)
    else:
        return None
    return number if number > 0 else None


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _history(value: object) -> list[dict[str, object]] | None:
    if not isinstance(value, list):
        return None
    by_month: dict[str, tuple[str, dict[str, object]]] = {}
    for point in value:
        if not isinstance(point, dict):
            continue
        at = _parse_timestamp(point.get("date"))
        visits = _as_positive_int(point.get("visits"))
        if at is not None and visits is not None:
            month = at.strftime("%Y-%m")
            snapshot_date = at.date().isoformat()
            current = by_month.get(month)
            if current is None or snapshot_date >= current[0]:
                by_month[month] = (snapshot_date, {"date": snapshot_date, "visits": visits})
    return [by_month[key][1] for key in sorted(by_month)] or None


def _countries(value: object) -> list[dict[str, object]] | None:
    if not isinstance(value, list):
        return None
    output = []
    for row in value:
        if not isinstance(row, dict):
            continue
        country = row.get("countryCode") or row.get("country")
        percentage = row.get("percentage")
        if not isinstance(country, str) or isinstance(percentage, bool):
            continue
        try:
            share = round(float(percentage) / 100.0, 4)
        except (TypeError, ValueError, OverflowError):
            continue
        if 0 <= share <= 1:
            entry: dict[str, object] = {"country": country, "share": share}
            visits = _as_positive_int(row.get("visits"))
            if visits is not None:
                entry["visits"] = visits
            output.append(entry)
    return output or None


def lookup(domain: str, original_input: str, cache=None, trace: ProviderTrace | None = None) -> VisitResult | None:
    query = urlencode({"domain": domain})
    url = f"{BASE_URL}?{query}"
    status, body, _headers = get_bytes(url, "application/json")
    if trace is not None:
        trace.http_status = status
    if status == 404:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderError("WebTrafficChecker returned invalid JSON; no retry was made.", SOURCE_NAME, status) from exc
    if not isinstance(payload, dict):
        raise ProviderError("WebTrafficChecker returned an unexpected JSON shape; no retry was made.", SOURCE_NAME, status)

    payload_domain = payload.get("domain")
    if isinstance(payload_domain, str) and payload_domain.lower().removeprefix("www.") != domain.lower().removeprefix("www."):
        return None
    traffic = payload.get("traffic")
    if not isinstance(traffic, dict):
        return None
    if traffic.get("isRanked") is False:
        return None
    rank_value = _as_positive_int(traffic.get("globalRank"))
    category = traffic.get("category")
    if rank_value is None or (
        isinstance(category, str) and category.strip().casefold() == "unranked website"
    ):
        return None
    visits = _as_positive_int(traffic.get("monthlyVisits"))
    analyzed_at_raw = payload.get("analyzedAt")
    analyzed_at = _parse_timestamp(analyzed_at_raw)
    if visits is None or analyzed_at is None:
        return None

    analyzed_at_text = analyzed_at_raw
    rank = {
        "value": rank_value,
        "list": "WebTrafficChecker global rank",
        "date": analyzed_at.date().isoformat(),
    }
    history = _history(payload.get("historicalRanks"))
    countries = _countries(payload.get("geography"))
    source_url = f"{DISPLAY_URL}{domain}"
    source = {
        "name": SOURCE_NAME,
        "layer": "primary",
        "method": "provider-modelled",
        "url": source_url,
        "api_url": url,
        "analyzed_at": analyzed_at_text,
    }
    history_source = {"name": SOURCE_NAME, "layer": "primary"} if history else None
    countries_source = {"name": SOURCE_NAME, "layer": "primary", "analyzed_at": analyzed_at_text} if countries else None
    return VisitResult(
        input=original_input,
        domain=domain,
        kind="estimate",
        monthly_visits=visits,
        monthly_visits_text=f"{visits:,}",
        period=None,
        analyzed_at=analyzed_at_text,
        range=None,
        confidence=None,
        rank=rank,
        history=history,
        history_source=history_source,
        countries=countries,
        countries_source=countries_source,
        source=source,
        calibration=None,
        fetched_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        cached=False,
        notes=[
            "This is WebTrafficChecker's modelled estimate, not the website owner's analytics.",
            "No independently measured error interval is available for this estimate.",
            "The provider's terms restrict substantially similar or competing services; the maintainers accept this risk for low-volume, cached lookups.",
        ],
    )
