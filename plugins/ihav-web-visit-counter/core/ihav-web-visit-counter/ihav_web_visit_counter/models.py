"""Stable JSON result contract shared by both host skills."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def result_from_dict(value: dict[str, Any]) -> VisitResult:
    """Load a result cache only when it still matches the public contract."""
    required = {
        "input", "domain", "kind", "monthly_visits", "period", "analyzed_at", "range", "confidence",
        "rank", "history", "history_source", "countries", "countries_source", "source",
        "calibration", "fetched_at", "cached", "notes",
    }
    if set(value) != required or value.get("kind") not in {"estimate", "rank_only"}:
        raise ValueError("Cached result does not match the current contract.")
    history = value.get("history")
    if history is not None and any(
        not isinstance(point, dict)
        or set(point) != {"date", "visits"}
        or not isinstance(point.get("date"), str)
        for point in history
    ):
        raise ValueError("Cached history does not match the current snapshot contract.")
    return VisitResult(**value)
