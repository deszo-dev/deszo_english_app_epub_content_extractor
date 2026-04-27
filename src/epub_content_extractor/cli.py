from __future__ import annotations

import argparse
from pathlib import Path

from .extractor import extract_epub


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
        help="Path to the output .txt file. Prints to stdout when omitted.",
    )
    parser.add_argument(
        "--debug-dir",
        type=Path,
        help="Write block scores, features, and keep/drop reasons to this directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    document = extract_epub(args.input, debug_dir=args.debug_dir)
    text = document.to_text()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
