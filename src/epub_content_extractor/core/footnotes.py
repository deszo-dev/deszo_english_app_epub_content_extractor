from __future__ import annotations

import re

from .constants import REFERENCE_WORDS
from .models import BlockFeatures, TextBlock
from .text import normalize_text


def build_footnote_index(blocks: list[TextBlock]) -> dict[str, str]:
    footnotes: dict[str, str] = {}
    for block in blocks:
        if block.position_ratio < 0.65:
            continue
        for bracket_id, dotted_id, note_text in re.findall(
            r"(?:^|\n)\s*(?:\[(\d+)\]|(\d+)\.)\s+(.+)",
            block.text,
        ):
            marker_id = bracket_id or dotted_id
            if marker_id:
                footnotes[marker_id] = note_text.strip()
    return footnotes


def remove_inline_footnote_markers(
    text: str,
    footnote_index: dict[str, str],
    chapter_blocks: list[TextBlock],
) -> str:
    marker_count = sum(
        len(re.findall(r"\[\d+\]|\(\d+\)", block.text)) for block in chapter_blocks
    )

    def bracket_replacer(match: re.Match[str]) -> str:
        marker_id = match.group(1)
        if marker_id in footnote_index:
            return ""
        confidence = inline_marker_confidence(
            text,
            match,
            bool(footnote_index),
            marker_count,
            bracket=True,
        )
        return "" if confidence > 0.6 else match.group(0)

    def paren_replacer(match: re.Match[str]) -> str:
        marker_id = match.group(1)
        if marker_id in footnote_index:
            confidence = inline_marker_confidence(
                text,
                match,
                True,
                marker_count,
                bracket=False,
            )
            return "" if confidence > 0.6 else match.group(0)
        confidence = inline_marker_confidence(
            text,
            match,
            bool(footnote_index),
            marker_count,
            bracket=False,
        )
        return "" if confidence > 0.8 else match.group(0)

    without_brackets = re.sub(r"\[(\d+)\]", bracket_replacer, text)
    without_markers = re.sub(r"\((\d+)\)", paren_replacer, without_brackets)
    return normalize_text(without_markers)


def inline_marker_confidence(
    text: str,
    match: re.Match[str],
    chapter_has_footnotes: bool,
    marker_count: int,
    *,
    bracket: bool,
) -> float:
    confidence = 0.0
    if chapter_has_footnotes:
        confidence += 0.5
    if marker_count > 3:
        confidence += 0.3
    if bracket:
        confidence += 0.2

    start, end = match.span()
    before = text[max(0, start - 24) : start]
    after = text[end : min(len(text), end + 24)]
    context = f"{before} {after}".lower()

    if re.search(r"\w\s*$", before) or re.match(r"^[.,;:]?", after):
        confidence += 0.3
    if re.match(r"^\s*\(\d+\)\s+[A-Z]", text[start:]):
        confidence -= 0.7
    if any(word in context for word in REFERENCE_WORDS):
        confidence -= 0.5
    return confidence


def is_footnote_block(block: TextBlock, features: BlockFeatures) -> bool:
    if block.position_ratio < 0.8:
        return False
    if features.footnote_lines_ratio > 0.5:
        return True
    return is_probable_footnote_block(block.text)


def is_probable_footnote_block(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return bool(re.match(r"^(\[\d+\]|\d+\.)\s+\S+", text))
    ids = []
    for line in lines:
        match = re.match(r"^(?:\[(\d+)\]|(\d+)\.)\s+\S+", line)
        if match:
            ids.append(int(match.group(1) or match.group(2)))
    return len(ids) >= 2 and ids == list(range(ids[0], ids[0] + len(ids)))
