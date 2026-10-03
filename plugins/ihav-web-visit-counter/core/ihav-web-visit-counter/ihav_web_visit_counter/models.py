"""Stable JSON result contract shared by both host skills."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


CONTRACT_VERSION = 2
PROVIDER_IDS = {"webtrafficchecker", "trafficlens", "tranco"}
PROVIDER_OUTCOMES = {"ok", "no_data", "blocked", "failed", "skipped", "cached"}


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
        "input", "domain", "kind", "monthly_visits", "period", "analyzed_at", "range", "confidence",
        "rank", "history", "history_source", "countries", "countries_source", "source",
        "calibration", "fetched_at", "cached", "notes",
    }
    freshness_fields = {"scraped_at", "stale"}
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
    required = base_required | freshness_fields | {"monthly_visits_text", "providers"}
    if set(value) != required or value.get("kind") not in {"estimate", "rank_only"}:
        raise ValueError("Cached result does not match the current contract.")
    visits = value.get("monthly_visits")
    if visits is not None and (isinstance(visits, bool) or not isinstance(visits, int)):
        raise ValueError("Cached monthly visits value has an unsupported type.")
    display_visits = value.get("monthly_visits_text")
    if display_visits is not None and not isinstance(display_visits, str):
        raise ValueError("Cached monthly visits display value has an unsupported type.")
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
    if history is not None and any(
        not isinstance(point, dict)
        or set(point) != {"date", "visits"}
        or not isinstance(point.get("date"), str)
        for point in history
    ):
        raise ValueError("Cached history does not match the current snapshot contract.")
    return VisitResult(**value)
