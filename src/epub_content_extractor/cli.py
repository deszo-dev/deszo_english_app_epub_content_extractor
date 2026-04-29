from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .exceptions import EpubReadError, ExtractionError, InputValidationError
from .extractor import extract_document

LOGGER = logging.getLogger("epub_content_extractor")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epub-content-extractor",
        description="Extract clean linear text from an EPUB file.",
    )
    parser.add_argument("input", type=Path, help="Path to the input .epub file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Path to the output .txt file. Writes to stdout when omitted.",
    )
    parser.add_argument(
        "--debug",
        type=Path,
        metavar="DIR",
        help="Write block decisions, score breakdowns, and features to this directory.",
    )
    parser.add_argument(
        "-d",
        "--debug-log",
        action="store_true",
        help="Enable detailed execution logging on stderr.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(debug=args.debug_log)

    try:
        LOGGER.info(
            "pipeline start input=%s output=%s debug=%s",
            args.input,
            args.output,
            args.debug,
        )
        document = extract_document(args.input, debug_dir=args.debug)
        text = document.to_text()
        write_output(args.output, text)
        LOGGER.info(
            "pipeline end chapters=%d debug_blocks=%d",
            len(document.chapters),
            len(document.debug_blocks),
        )
        return 0
    except InputValidationError as exc:
        LOGGER.error("%s", exc)
        return 1
    except EpubReadError as exc:
        LOGGER.error("%s", exc)
        return 1
    except ExtractionError as exc:
        LOGGER.error("%s", exc)
        return 1
    except OSError as exc:
        LOGGER.error("system error: %s", exc)
        return 2


def configure_logging(*, debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
        stream=sys.stderr,
        force=True,
    )


def write_output(output_path: Path | None, text: str) -> None:
    if output_path is None:
        sys.stdout.write(text)
        if text:
            sys.stdout.write("\n")
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
