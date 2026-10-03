"""One-shot HTTP access with bounded redirect and block handling."""

from __future__ import annotations

import http.client
from email.message import Message
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from . import __version__
from .errors import BlockedError, ProviderError


USER_AGENT = f"ihav-web-visit-counter/{__version__} (+https://github.com/hiendang7613/ihav-web-visit-counter)"
TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 32 * 1024 * 1024


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


_OPENER = build_opener(_NoRedirect())
_CHALLENGE_MARKERS = (
    "verify you are human", "checking your browser", "captcha", "just a moment",
    "challenge-platform", "bot detected", "unusual traffic", "access denied",
    "temporarily blocked", "too many requests",
)


def _headers(value: Message | dict[str, str] | None) -> dict[str, str]:
    if value is None:
        return {}
    return {str(key).lower(): str(item) for key, item in value.items()}


def _is_challenge(body: bytes, headers: dict[str, str] | None = None) -> bool:
    content_type = (headers or {}).get("content-type", "").split(";", 1)[0].strip().lower()
    looks_like_html = content_type in {"text/html", "application/xhtml+xml"} or body.lstrip().startswith(b"<")
    if not looks_like_html:
        return False
    text = body[:16384].decode("utf-8", errors="ignore").lower()
    return any(marker in text for marker in _CHALLENGE_MARKERS)


class _SameHostHTTPSRedirect(HTTPRedirectHandler):
    """Allow redirects only within one explicitly approved HTTPS host."""

    def __init__(self, allowed_host: str):
        super().__init__()
        self.allowed_host = allowed_host.lower().rstrip(".")

    def redirect_request(self, request, response, code, message, headers, new_url):
        try:
            origin = urlsplit(request.full_url)
            target = urlsplit(new_url)
            allowed = (
                origin.scheme == "https"
                and origin.hostname is not None
                and origin.hostname.lower().rstrip(".") == self.allowed_host
                and origin.port in {None, 443}
                and target.scheme == "https"
                and target.hostname is not None
                and target.hostname.lower().rstrip(".") == self.allowed_host
                and target.port in {None, 443}
                and target.username is None
                and target.password is None
            )
        except ValueError:
            return None
        if not allowed:
            return None
        return super().redirect_request(request, response, code, message, headers, new_url)


def _read_limited(stream, limit: int, host: str) -> bytes:
    try:
        return stream.read(limit)
    except (OSError, http.client.HTTPException) as exc:
        raise ProviderError(f"Could not read the response from {host}; no retry was made.", source=host) from exc


def get_bytes(url: str, accept: str, redirect_host: str | None = None) -> tuple[int, bytes, dict[str, str]]:
    """Make one GET. Redirects are disabled unless a source opts into same-host HTTPS only."""
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept}, method="GET")
    source_host = urlsplit(url).hostname or "unknown source"
    opener = _OPENER if redirect_host is None else build_opener(_SameHostHTTPSRedirect(redirect_host))
    try:
        response = opener.open(request, timeout=TIMEOUT_SECONDS)
    except HTTPError as exc:
        if exc.code in {401, 403, 429}:
            raise BlockedError(
                f"{source_host} returned HTTP {exc.code}; stopped this source without retrying.",
                source=source_host,
            ) from exc
        response_headers = _headers(exc.headers)
        if 300 <= exc.code < 400 and "location" in response_headers:
            exc.close()
            raise ProviderError(
                f"{source_host} returned a redirect; redirect not followed.",
                source=source_host,
            ) from exc
        body = _read_limited(exc, 16384, source_host)
        if _is_challenge(body, response_headers):
            raise BlockedError(
                f"{source_host} returned a challenge page; stopped this source without retrying.",
                source=source_host,
            ) from exc
        if exc.code == 404:
            return 404, body, response_headers
        raise ProviderError(
            f"{source_host} returned HTTP {exc.code}; no retry was made.",
            source=source_host,
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ProviderError(
            f"Could not reach {source_host}: {exc.reason if isinstance(exc, URLError) else exc}",
            source=source_host,
        ) from exc

    with response:
        status = int(response.status)
        response_headers = _headers(response.headers)
        body = _read_limited(response, MAX_RESPONSE_BYTES + 1, source_host)
    if status in {401, 403, 429} or _is_challenge(body, response_headers):
        raise BlockedError(
            f"{source_host} returned HTTP {status} or a challenge page; stopped this source without retrying.",
            source=source_host,
        )
    if status >= 400:
        raise ProviderError(f"{source_host} returned HTTP {status}; no retry was made.", source=source_host)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ProviderError(f"{source_host} response exceeded the 32 MiB safety limit.", source=source_host)
    return status, body, response_headers
