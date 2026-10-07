"""Ordered provider orchestration for one normalized website."""

from __future__ import annotations

from pathlib import Path

from .cache import Cache, default_cache_dir
from .errors import BlockedError, InternalError, NoDataError, ProviderError, VisitError
from .models import ProviderTrace, VisitResult
from .normalize import normalize_domain
from .providers import PROVIDERS


def _provider_name(provider) -> str:
    return getattr(provider, "SOURCE_NAME", provider.__name__.rsplit(".", 1)[-1])


def _provider_id(provider) -> str:
    return provider.PROVIDER_ID


def _failure_detail(provider, error: VisitError) -> str:
    name = _provider_name(provider)
    detail = error.message
    if error.source:
        detail = detail.replace(error.source, name)
    return detail


def _failure_note(provider, error: VisitError) -> str:
    return f"{_provider_name(provider)} failed: {_failure_detail(provider, error)}"


def _short_detail(value: str | None) -> str | None:
    if value is None:
        return None
    compact = " ".join(value.split())
    return compact[:240] or None


def _attempt(
    provider,
    outcome: str,
    http_status: int | None = None,
    detail: str | None = None,
) -> dict[str, object]:
    return {
        "name": _provider_id(provider),
        "outcome": outcome,
        "http_status": http_status,
        "detail": _short_detail(detail),
    }


def _with_cache_notes(result: VisitResult, cache: Cache) -> VisitResult:
    for warning in cache.warnings:
        if warning not in result.notes:
            result.notes.append(warning)
    return result


def _cached_provider_outcome(result: VisitResult) -> list[dict[str, object]]:
    source_name = (result.source or {}).get("name")
    provider = next((item for item in PROVIDERS if _provider_name(item) == source_name), None)
    if provider is None:
        return []
    original_status = next(
        (
            item.get("http_status")
            for item in result.providers
            if item.get("name") == _provider_id(provider) and item.get("outcome") == "ok"
        ),
        None,
    )
    if isinstance(original_status, bool) or not isinstance(original_status, int):
        original_status = None
    return [
        _attempt(
            provider,
            "cached",
            original_status,
            "Served from the 24-hour cache; the provider was not contacted in this run.",
        )
    ]


def lookup(input_value: str, cache_dir: Path | None = None) -> VisitResult:
    domain = normalize_domain(input_value)
    cache = Cache(cache_dir or default_cache_dir())
    cached = cache.get_result(domain)
    # A rank-only result must not hide a recovered primary estimate for 24 hours.
    if cached is not None and cached.kind != "rank_only":
        cached.input = input_value
        # Keep the original fetched_at on the result, but do not replay an earlier
        # provider block as if it happened during this cache-hit request.
        cached.providers = _cached_provider_outcome(cached)
        return cached

    failures: list[tuple[object, VisitError]] = []
    outcomes: list[dict[str, object]] = []
    outcome_notes: list[tuple[object, str]] = []
    primary_no_data = False
    for index, provider in enumerate(PROVIDERS):
        name = _provider_name(provider)
        trace = ProviderTrace()
        try:
            result = provider.lookup(domain, input_value, cache, trace)
        except (BlockedError, ProviderError) as exc:
            failures.append((provider, exc))
            outcome = "blocked" if isinstance(exc, BlockedError) else "failed"
            http_status = exc.http_status if exc.http_status is not None else trace.http_status
            outcomes.append(_attempt(provider, outcome, http_status, _failure_detail(provider, exc)))
            outcome_notes.append((provider, _failure_note(provider, exc)))
            continue
        except Exception as exc:
            outcomes.append(_attempt(provider, "failed", trace.http_status, "Unexpected provider error."))
            error = InternalError("Unexpected internal error; no retry was made.")
            error.providers = outcomes
            raise error from exc

        if result is None:
            if index == 0:
                primary_no_data = True
            detail = f"{name} returned no usable result."
            outcomes.append(_attempt(provider, "no_data", trace.http_status, detail))
            outcome_notes.append((provider, detail))
            continue

        outcomes.append(_attempt(provider, "ok", trace.http_status))
        if outcome_notes:
            result.notes.append(
                f"Using this fallback after {'; '.join(item[1] for item in outcome_notes)}. No blocked source was retried."
            )
        outcomes.extend(
            _attempt(
                skipped_provider,
                "skipped",
                detail="Not called because an earlier provider returned a usable result.",
            )
            for skipped_provider in PROVIDERS[index + 1 :]
        )
        result.providers = outcomes
        # Cache estimates from every provider for 24 hours; never cache rank-only output.
        # Cache warnings describe this run only, so they are added after storing.
        if result.kind == "estimate":
            cache.put_result(result)
        return _with_cache_notes(result, cache)

    if primary_no_data:
        later_failure_notes = [
            _failure_note(provider, error)
            for provider, error in failures
            if provider is not PROVIDERS[0]
        ]
        raise NoDataError(
            f"No usable visit estimate or rank was available for {domain}; no visits were inferred.",
            notes=later_failure_notes,
            providers=outcomes,
        )

    if failures:
        first_provider, first_error = failures[0]
        other_outcomes = [message for provider, message in outcome_notes if provider is not first_provider]
        message = first_error.message
        if other_outcomes:
            message = f"{message} Other provider outcome: {'; '.join(other_outcomes)}."
        error = type(first_error)(message, first_error.source, first_error.http_status)
        error.providers = outcomes
        raise error

    raise NoDataError(
        f"No usable visit estimate or rank was available for {domain}; no visits were inferred.",
        providers=outcomes,
    )
