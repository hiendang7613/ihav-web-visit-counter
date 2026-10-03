"""Typed failures used by the CLI and provider adapters."""

from __future__ import annotations


class VisitError(Exception):
    """An expected failure with a stable CLI status and machine code."""

    exit_code = 5
    code = "source_error"

    def __init__(self, message: str, source: str | None = None):
        super().__init__(message)
        self.message = message
        self.source = source


class InvalidInputError(VisitError):
    exit_code = 64
    code = "invalid_input"


class NoDataError(VisitError):
    exit_code = 2
    code = "no_data"

    def __init__(self, message: str, notes: list[str] | None = None):
        super().__init__(message)
        self.notes = list(notes or [])


class BlockedError(VisitError):
    exit_code = 4
    code = "blocked"


class ProviderError(VisitError):
    exit_code = 5
    code = "provider_error"


class CacheError(VisitError):
    exit_code = 5
    code = "cache_error"
