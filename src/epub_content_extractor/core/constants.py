from __future__ import annotations

BLOCK_TAGS: tuple[str, ...] = ("p", "div", "section", "article", "li", "blockquote")
HEADING_TAGS: tuple[str, ...] = ("h1", "h2", "h3", "h4", "h5", "h6")
DIALOGUE_MARKERS: tuple[str, ...] = ("-", '"', "'", "—", "“", "‘")

MIN_CHARS = 25
MIN_ALPHA_RATIO = 0.6
MAX_DIGIT_RATIO = 0.3
KEEP_SCORE = 0.3
DROP_SCORE = 0.0

BOILERPLATE: tuple[str, ...] = (
    "all rights reserved",
    "copyright",
    "isbn",
    "published by",
    "project gutenberg",
    "table of contents",
)

REFERENCE_WORDS: frozenset[str] = frozenset(
    {"equation", "figure", "fig", "table", "appendix", "example"}
)
