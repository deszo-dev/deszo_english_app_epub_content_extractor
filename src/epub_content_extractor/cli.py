from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from .config import EXTRACTOR_VERSION
from .extractor import extract_epub_content


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="epub-content-extractor")
    parser.add_argument("--version", action="store_true", help="Print CLI version.")

    subparsers = parser.add_subparsers(dest="command")
    extract_parser = subparsers.add_parser("extract", help="Extract structured EPUB content.")
    extract_parser.add_argument("input", type=Path, help="Path to the input EPUB file.")
    extract_parser.add_argument(
        "--output",
        type=str,
        default="-",
        help="Write JSON result to PATH. Use - for stdout.",
    )
    extract_parser.add_argument(
        "--config",
        type=str,
        help="Path to JSON config file. Use - to read config from stdin.",
    )
    extract_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    extract_parser.add_argument(
        "--include-debug",
        action="store_true",
        help="Include top-level debug information.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        sys.stdout.write(f"{EXTRACTOR_VERSION}\n")
        return 0

    if args.command != "extract":
        parser.print_help(sys.stdout)
        return 2

    try:
        config = load_config(args.config)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 4

    if args.include_debug:
        config["include_debug"] = True

    result = extract_epub_content(args.input, config=config)
    exit_code = cli_exit_code_for_result(result)

    try:
        write_json_result(
            output_target=args.output,
            result=result,
            pretty=args.pretty,
        )
    except OSError as exc:
        sys.stderr.write(f"output write failed: {exc}\n")
        return 3

    return exit_code


def load_config(config_path: str | None) -> dict[str, object]:
    if config_path is None:
        return {}
    if config_path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(config_path).read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid config JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("invalid config JSON: top-level config must be an object")
    return payload


def cli_exit_code_for_result(result: dict[str, object]) -> int:
    if result["status"] == "succeeded":
        return 0
    error = result.get("error", {})
    if not isinstance(error, dict):
        return 99
    code = error.get("code")
    if code == "invalid_config":
        return 4
    if code == "internal_error":
        return 99
    return 1


def write_json_result(
    *,
    output_target: str,
    result: dict[str, object],
    pretty: bool,
) -> None:
    serialized = json.dumps(
        result,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    )
    if output_target == "-":
        sys.stdout.write(serialized)
        sys.stdout.write("\n")
        return

    output_path = Path(output_target)
    parent = output_path.parent
    if not parent.exists() or not parent.is_dir():
        raise OSError("output directory does not exist")

    fd, temp_name = tempfile.mkstemp(
        dir=str(parent),
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(serialized)
            handle.write("\n")
        os.replace(temp_name, output_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


if __name__ == "__main__":
    raise SystemExit(main())
