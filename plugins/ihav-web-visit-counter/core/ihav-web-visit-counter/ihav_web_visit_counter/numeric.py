"""Bound decimal-string conversion consistently across supported Python versions."""

from __future__ import annotations


# Match CPython 3.11's default conversion ceiling without changing host settings.
MAX_DECIMAL_DIGITS = 4300


def decimal_integer(value: str) -> int | None:
    if len(value) > MAX_DECIMAL_DIGITS or not value.isdecimal():
        return None
    try:
        return int(value)
    except ValueError:
        # A host can configure a lower conversion ceiling.
        return None


def json_integer(value: str) -> int | None:
    """Decode bounded JSON integers while retaining zero and signed values."""
    negative = value.startswith("-")
    digits = value[1:] if negative else value
    number = decimal_integer(digits)
    return -number if negative and number is not None else number
