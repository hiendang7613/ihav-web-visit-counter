"""Command-line interface for one-site monthly traffic lookup."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .errors import InvalidInputError, VisitError
from .render import render
from .service import lookup


class _UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _UsageError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="ihav-web-visit-counter",
        description="Look up a website's monthly traffic estimate, or its rank when no estimate exists.",
    )
    parser.add_argument("website", nargs="?", help="website URL or domain")
    parser.add_argument("--json", action="store_true", help="print the result contract as JSON")
    parser.add_argument("--cache-dir", type=Path, help="override the default .ihav_space cache directory")
    return parser


def _write_error(message: str, code: str, exit_code: int, source: str | None, json_mode: bool) -> int:
    error: dict[str, object] = {"code": code, "message": message}
    if source:
        error["source"] = source
    if json_mode:
        print(json.dumps({"error": error}, ensure_ascii=False))
    else:
        print(f"Error: {message}", file=sys.stderr)
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in arguments
    parser = _parser()
    try:
        args = parser.parse_args(arguments)
    except _UsageError as exc:
        return _write_error(str(exc), "invalid_arguments", 64, None, json_mode)

    if not args.website:
        return _write_error("Provide a website URL or domain.", "invalid_input", 64, None, args.json)

    try:
        result = lookup(args.website, args.cache_dir)
    except InvalidInputError as exc:
        return _write_error(exc.message, exc.code, exc.exit_code, exc.source, args.json)
    except VisitError as exc:
        return _write_error(exc.message, exc.code, exc.exit_code, exc.source, args.json)
    except Exception:
        return _write_error(
            "Unexpected internal error; no retry was made.",
            "internal_error",
            5,
            None,
            args.json,
        )

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, separators=(",", ":")))
    else:
        print(render(result))
    return 0
