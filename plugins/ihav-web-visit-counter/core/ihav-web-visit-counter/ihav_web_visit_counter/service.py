"""Ordered provider orchestration for one normalized website."""

from __future__ import annotations

from pathlib import Path

from .cache import Cache, default_cache_dir
from .errors import BlockedError, NoDataError, ProviderError, VisitError
from .models import VisitResult
from .normalize import normalize_domain
from .providers import PROVIDERS


def _provider_name(provider) -> str:
    return getattr(provider, "SOURCE_NAME", provider.__name__.rsplit(".", 1)[-1])


def _with_cache_notes(result: VisitResult, cache: Cache) -> VisitResult:
    for warning in cache.warnings:
        if warning not in result.notes:
            result.notes.append(warning)
    return result


def lookup(input_value: str, cache_dir: Path | None = None) -> VisitResult:
    domain = normalize_domain(input_value)
    cache = Cache(cache_dir or default_cache_dir())
    cached = cache.get_result(domain)
    # A rank-only result must not hide a recovered primary estimate for 24 hours.
    if cached is not None and cached.kind != "rank_only":
        cached.input = input_value
        return cached

    failures: list[tuple[object, VisitError]] = []
    outcomes: list[tuple[object, str]] = []
    for provider in PROVIDERS:
        name = _provider_name(provider)
        try:
            result = provider.lookup(domain, input_value, cache)
        except (BlockedError, ProviderError) as exc:
            failures.append((provider, exc))
            outcomes.append((provider, f"{name} failed: {exc.message}"))
            continue

        if result is None:
            outcomes.append((provider, f"{name} returned no usable result"))
            continue

        if outcomes:
            result.notes.append(
                f"Using this fallback after {'; '.join(item[1] for item in outcomes)}. No blocked source was retried."
            )
        _with_cache_notes(result, cache)
        # Cache estimates from every provider for 24 hours; never cache rank-only output.
        if result.kind == "estimate":
            cache.put_result(result)
        return _with_cache_notes(result, cache)

    if failures:
        first_provider, first_error = failures[0]
        other_outcomes = [message for provider, message in outcomes if provider is not first_provider]
        message = first_error.message
        if other_outcomes:
            message = f"{message} Other provider outcome: {'; '.join(other_outcomes)}."
        raise type(first_error)(message, first_error.source)

    raise NoDataError(f"No usable visit estimate or rank was available for {domain}; no visits were inferred.")
