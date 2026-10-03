"""Plain terminal rendering that keeps type, period and attribution visible."""

from __future__ import annotations

from .models import VisitResult


_SPARKS = "▁▂▃▄▅▆▇█"


def _sparkline(values: list[int]) -> str:
    if not values:
        return ""
    low, high = min(values), max(values)
    if low == high:
        return _SPARKS[3] * len(values)
    return "".join(_SPARKS[round((value - low) * (len(_SPARKS) - 1) / (high - low))] for value in values)


def _format_visits(value: int | str) -> str:
    return value if isinstance(value, str) else f"{value:,}"


def render(result: VisitResult) -> str:
    lines = [f"{result.domain}"]
    if result.kind == "estimate" and (
        result.monthly_visits is not None or result.monthly_visits_text is not None
    ):
        visits_text = result.monthly_visits_text
        if visits_text is None:
            visits_text = _format_visits(result.monthly_visits)
        details = []
        if result.stale:
            details.append("stale")
        if result.scraped_at:
            details.append(f"scraped {result.scraped_at[:10]}")
        elif result.stale:
            details.append("scrape date unavailable")
        elif result.analyzed_at:
            details.append(f"analyzed {result.analyzed_at[:10]}")
        else:
            details.append("date unavailable")
        lines.append(
            f"  ~{visits_text} estimated monthly visits · {' · '.join(details)}"
        )
        if result.range:
            lines.append(f"  Provider range: {_format_visits(result.range['low'])}–{_format_visits(result.range['high'])}")
        else:
            lines.append("  Error range: not independently measured")
    elif result.kind == "rank_only" and result.rank:
        lines.append(f"  Tranco rank #{result.rank['value']:,} · list retrieved {result.rank['date']}")
        lines.append("  Monthly visits: unknown. Rank is not a visit count.")

    if result.history:
        values = [int(point["visits"]) for point in result.history]
        dates = f"{result.history[0]['date']} → {result.history[-1]['date']}"
        lines.append(f"  History snapshots {dates}  {_sparkline(values)}")
    if result.countries:
        countries = " · ".join(
            f"{item['country']} {float(item['share']) * 100:.1f}%" for item in result.countries[:5]
        )
        lines.append(f"  Top countries: {countries}")
    if result.source:
        lines.append(f"  Source: {result.source['name']} · {result.source['url']}")
    if result.cached:
        lines.append("  Cached result · refreshed at most once per 24 hours")
    for note in result.notes:
        lines.append(f"  Note: {note}")
    return "\n".join(lines)
