from __future__ import annotations

import sys
import unittest
import http.client
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins/ihav-web-visit-counter/core/ihav-web-visit-counter"
sys.path.insert(0, str(CORE))

from ihav_web_visit_counter.errors import BlockedError, ProviderError
from ihav_web_visit_counter.http import USER_AGENT, _SameHostHTTPSRedirect, get_bytes


class HTTPPolicyTests(unittest.TestCase):
    def test_http_403_stops_after_one_request(self):
        blocked = HTTPError("https://webtrafficchecker.com/api/traffic", 403, "Forbidden", {}, BytesIO(b"Access denied"))
        with patch("ihav_web_visit_counter.http._OPENER.open", side_effect=blocked) as opener:
            with self.assertRaises(BlockedError):
                get_bytes("https://webtrafficchecker.com/api/traffic?domain=example.com", "application/json")
        opener.assert_called_once()
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), USER_AGENT)
        self.assertEqual(request.get_method(), "GET")

    def test_json_with_captcha_domain_text_is_not_a_challenge(self):
        response = BytesIO(b'{"domain":"recaptcha.net"}')
        response.status = 200
        response.headers = {"Content-Type": "application/json"}
        with patch("ihav_web_visit_counter.http._OPENER.open", return_value=response):
            status, body, headers = get_bytes("https://webtrafficchecker.com/api/traffic", "application/json")
        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"domain":"recaptcha.net"}')
        self.assertEqual(headers["content-type"], "application/json")

    def test_html_challenge_on_http_200_is_blocked(self):
        response = BytesIO(b"<html><title>Verify you are human</title></html>")
        response.status = 200
        response.headers = {"Content-Type": "text/html; charset=utf-8"}
        with patch("ihav_web_visit_counter.http._OPENER.open", return_value=response):
            with self.assertRaises(BlockedError):
                get_bytes("https://webtrafficchecker.com/api/traffic", "application/json")

    def test_truncated_response_body_maps_to_provider_error(self):
        class TruncatedResponse:
            status = 200
            headers = {"Content-Type": "application/json"}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                raise http.client.IncompleteRead(b"partial")

        with patch("ihav_web_visit_counter.http._OPENER.open", return_value=TruncatedResponse()):
            with self.assertRaises(ProviderError) as raised:
                get_bytes("https://webtrafficchecker.com/api/traffic", "application/json")
        self.assertIn("Could not read the response", raised.exception.message)

    def test_tranco_redirect_handler_accepts_only_same_host_https(self):
        handler = _SameHostHTTPSRedirect("tranco-list.eu")
        request = Request("https://tranco-list.eu/top-1m.csv.zip")
        allowed = handler.redirect_request(
            request, None, 302, "Found", {}, "https://tranco-list.eu/lists/latest.csv.zip"
        )
        cross_host = handler.redirect_request(
            request, None, 302, "Found", {}, "https://cdn.example.net/list.csv.zip"
        )
        downgrade = handler.redirect_request(
            request, None, 302, "Found", {}, "http://tranco-list.eu/list.csv.zip"
        )
        self.assertIsNotNone(allowed)
        self.assertIsNone(cross_host)
        self.assertIsNone(downgrade)


if __name__ == "__main__":
    unittest.main()
