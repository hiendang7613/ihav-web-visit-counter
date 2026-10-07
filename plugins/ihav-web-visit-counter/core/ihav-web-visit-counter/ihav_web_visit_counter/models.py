"""Stable JSON result contract shared by both host skills."""

from __future__ import annotations

import math
import re
from dataclasses import MISSING, asdict, dataclass, field, fields
from decimal import Decimal, InvalidOperation
from typing import Any


CONTRACT_VERSION = 2
PROVIDER_IDS = {"webtrafficchecker", "trafficlens", "tranco"}
PROVIDER_OUTCOMES = {"ok", "no_data", "blocked", "failed", "skipped", "cached"}
_DISPLAY_VISITS = re.compile(r"^(?:\d+(?:\.\d+)?|\d{1,3}(?:,\d{3})+)[KMBT]?$", re.IGNORECASE)


def _positive_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _visit_display(value: str) -> bool:
    if not _DISPLAY_VISITS.fullmatch(value):
        return False
    number = value[:-1] if value[-1:].upper() in {"K", "M", "B", "T"} else value
    try:
        return Decimal(number.replace(",", "")) > 0
    except InvalidOperation:
        return False


@dataclass
class ProviderTrace:
    """Request-local HTTP status recorded by one provider adapter."""

    http_status: int | None = None


@dataclass
class VisitResult:
    input: str
    domain: str
    kind: str
    monthly_visits: int | None
    period: str | None
    analyzed_at: str | None
    range: dict[str, Any] | None
    confidence: str | None
    rank: dict[str, Any] | None
    history: list[dict[str, Any]] | None
    history_source: dict[str, Any] | None
    countries: list[dict[str, Any]] | None
    countries_source: dict[str, Any] | None
    source: dict[str, Any] | None
    calibration: dict[str, Any] | None
    fetched_at: str
    cached: bool
    notes: list[str]
    monthly_visits_text: str | None = None
    scraped_at: str | None = None
    stale: bool = False
    providers: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["contract_version"] = CONTRACT_VERSION
        return value


def result_from_dict(value: dict[str, Any]) -> VisitResult:
    """Load a result cache only when it still matches the public contract."""
    value = dict(value)
    contract_version = value.pop("contract_version", None)
    if contract_version not in {None, 1, CONTRACT_VERSION} or isinstance(contract_version, bool):
        raise ValueError("Cached result uses an unsupported contract version.")
    base_required = {
        item.name for item in fields(VisitResult)
        if item.default is MISSING and item.default_factory is MISSING
    }
    if not base_required.issubset(value):
        raise ValueError("Cached result does not match the current contract.")
    value.setdefault("scraped_at", None)
    value.setdefault("stale", False)
    value.setdefault("providers", [])
    if "monthly_visits_text" not in value:
        old_visits = value.get("monthly_visits")
        if isinstance(old_visits, str):
            value["monthly_visits"] = None
            display_visits = old_visits
        elif isinstance(old_visits, int) and not isinstance(old_visits, bool):
            display_visits = f"{old_visits:,}"
        else:
            display_visits = None
        value["monthly_visits_text"] = display_visits
    required = {item.name for item in fields(VisitResult)}
    if set(value) != required or value.get("kind") not in {"estimate", "rank_only"}:
        raise ValueError("Cached result does not match the current contract.")
    if any(not isinstance(value[name], str) or not value[name] for name in ("input", "domain", "fetched_at")):
        raise ValueError("Cached result identity or fetch timestamp is invalid.")
    if not isinstance(value["cached"], bool) or not isinstance(value["notes"], list) or any(
        not isinstance(note, str) for note in value["notes"]
    ):
        raise ValueError("Cached result state or notes are invalid.")
    for name in ("period", "analyzed_at", "confidence"):
        if value[name] is not None and not isinstance(value[name], str):
            raise ValueError("Cached result metadata has an unsupported type.")
    visits = value.get("monthly_visits")
    if visits is not None and not _positive_integer(visits):
        raise ValueError("Cached monthly visits must be a positive integer.")
    display_visits = value.get("monthly_visits_text")
    if display_visits is not None and (not isinstance(display_visits, str) or not _visit_display(display_visits)):
        raise ValueError("Cached monthly visits display value is invalid.")
    if value["kind"] == "estimate" and visits is None and display_visits is None:
        raise ValueError("Cached estimate has no visit value.")
    if value.get("kind") == "rank_only" and (visits is not None or display_visits is not None):
        raise ValueError("Cached rank-only result cannot contain a visit value.")
    if value.get("scraped_at") is not None and not isinstance(value.get("scraped_at"), str):
        raise ValueError("Cached scrape timestamp has an unsupported type.")
    if not isinstance(value.get("stale"), bool):
        raise ValueError("Cached freshness marker has an unsupported type.")
    providers = value.get("providers")
    if not isinstance(providers, list):
        raise ValueError("Cached provider outcomes have an unsupported type.")
    for provider in providers:
        if not isinstance(provider, dict) or set(provider) != {"name", "outcome", "http_status", "detail"}:
            raise ValueError("Cached provider outcome does not match the current contract.")
        if provider.get("name") not in PROVIDER_IDS or provider.get("outcome") not in PROVIDER_OUTCOMES:
            raise ValueError("Cached provider outcome has an unsupported name or state.")
        status = provider.get("http_status")
        if status is not None and (isinstance(status, bool) or not isinstance(status, int)):
            raise ValueError("Cached provider HTTP status has an unsupported type.")
        if provider.get("detail") is not None and not isinstance(provider.get("detail"), str):
            raise ValueError("Cached provider detail has an unsupported type.")
    history = value.get("history")
    if history is not None and (not isinstance(history, list) or any(
        not isinstance(point, dict)
        or set(point) != {"date", "visits"}
        or not isinstance(point.get("date"), str)
        or not _positive_integer(point.get("visits"))
        for point in history
    )):
        raise ValueError("Cached history does not match the current snapshot contract.")
    rank = value["rank"]
    if rank is not None and (
        not isinstance(rank, dict) or not _positive_integer(rank.get("value"))
        or not isinstance(rank.get("date"), str) or not isinstance(rank.get("list"), str)
    ):
        raise ValueError("Cached rank is invalid.")
    countries = value["countries"]
    if countries is not None:
        if not isinstance(countries, list):
            raise ValueError("Cached country shares are invalid.")
        for country in countries:
            if not isinstance(country, dict) or not isinstance(country.get("country"), str):
                raise ValueError("Cached country shares are invalid.")
            share = country.get("share")
            if not isinstance(share, (int, float)) or isinstance(share, bool) or not 0 <= share <= 1 or not math.isfinite(share):
                raise ValueError("Cached country share is invalid.")
            if "visits" in country and not _positive_integer(country["visits"]):
                raise ValueError("Cached country visits are invalid.")
    source = value["source"]
    if not isinstance(source, dict) or any(not isinstance(source.get(name), str) for name in ("name", "url")):
        raise ValueError("Cached source attribution is invalid.")
    bounds = value["range"]
    if bounds is not None and (
        not isinstance(bounds, dict) or any(
            isinstance(bounds.get(name), bool) or not isinstance(bounds.get(name), (int, str))
            for name in ("low", "high")
        )
    ):
        raise ValueError("Cached visit range is invalid.")
    return VisitResult(**value)
