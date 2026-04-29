from __future__ import annotations

import re
import unicodedata

import regex
from rapidfuzz import fuzz

from .constants import DIALOGUE_MARKERS
from .models import BlockFeatures, TextBlock


def extract_features(block: TextBlock, seen_texts: list[str]) -> BlockFeatures:
    text = block.text
    chars = len(text)
    words = regex.findall(r"\p{L}+(?:['-]\p{L}+)?", text)
    letters = sum(1 for char in text if char.isalpha())
    digits = sum(1 for char in text if char.isdigit())
    punctuation = sum(1 for char in text if unicodedata.category(char).startswith("P"))
    sentence_count = len(re.findall(r"[.!?]+(?:\s|$)", text))

    return BlockFeatures(
        length_chars=chars,
        length_words=len(words),
        avg_word_length=average_word_length(words),
        punctuation_ratio=punctuation / chars if chars else 0.0,
        alpha_ratio=letters / chars if chars else 0.0,
        digit_ratio=digits / chars if chars else 0.0,
        sentence_count=sentence_count,
        is_uppercase=is_uppercase_text(text),
        has_dialogue_markers=any(marker in text for marker in DIALOGUE_MARKERS),
        starts_with_number=bool(re.match(r"^\s*\(?\d+", text)),
        ends_with_punctuation=bool(re.search(r"[.!?;:,'\")\]]$", text)),
        repetition_score=repetition_score(text, seen_texts),
        footnote_lines_ratio=footnote_lines_ratio(text),
    )


def is_uppercase_text(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    return bool(letters) and uppercase_ratio(letters) > 0.8


def repetition_score(text: str, seen_texts: list[str]) -> float:
    if not seen_texts:
        return 0.0
    normalized = text.lower().strip()
    candidates = [
        candidate
        for candidate in seen_texts
        if abs(len(candidate) - len(text)) <= max(20, len(text) * 0.4)
    ]
    if not candidates:
        return 0.0
    return max(
        fuzz.ratio(normalized, candidate.lower().strip()) / 100
        for candidate in candidates[-200:]
    )


def footnote_lines_ratio(text: str) -> float:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        lines = [text.strip()]
    matches = sum(1 for line in lines if re.match(r"^(\[\d+\]|\d+\.)\s+\S+", line))
    return matches / len(lines) if lines else 0.0


def average_word_length(words: list[str]) -> float:
    return (sum(len(word) for word in words) / len(words)) if words else 0.0


def uppercase_ratio(letters: list[str]) -> float:
    return sum(char.isupper() for char in letters) / len(letters)
