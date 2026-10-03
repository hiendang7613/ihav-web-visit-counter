"""Normalize user input without guessing public-suffix boundaries."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

from .errors import InvalidInputError


_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


def normalize_domain(value: str) -> str:
    """Return a lowercase ASCII host; preserve non-www subdomains as entered."""
    raw = value.strip()
    if not raw or any(character.isspace() for character in raw):
        raise InvalidInputError("Enter a website URL or domain, such as example.com.")

    candidate = raw if "://" in raw else "//" + raw
    try:
        parsed = urlsplit(candidate)
        host = parsed.hostname
    except ValueError as exc:
        raise InvalidInputError("The website URL is not valid.") from exc
    if not host:
        raise InvalidInputError("Enter a website URL or domain, such as example.com.")

    host = host.rstrip(".").lower()
    if host.startswith("www."):
        host = host[4:]
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass

    try:
        ascii_host = host.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise InvalidInputError("The website domain contains an invalid international name.") from exc

    if len(ascii_host) > 253 or "." not in ascii_host:
        raise InvalidInputError("Enter a full website domain, such as example.com.")
    labels = ascii_host.split(".")
    if any(not _LABEL.fullmatch(label) for label in labels):
        raise InvalidInputError("The website domain contains an invalid label.")
    return ascii_host
