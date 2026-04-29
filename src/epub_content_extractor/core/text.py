from __future__ import annotations

import re
import unicodedata

import ftfy


def normalize_text(text: str) -> str:
    normalized = ftfy.fix_text(text)
    normalized = unicodedata.normalize("NFC", normalized)
    normalized = normalized.replace("\xa0", " ")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\s+([,.;:!?])", r"\1", normalized)
    normalized = re.sub(r"([\(\[\{])\s+", r"\1", normalized)
    normalized = re.sub(r"\s+([\)\]\}])", r"\1", normalized)
    normalized = re.sub(r"\s+\n", "\n", normalized)
    normalized = re.sub(r"\n\s+", "\n", normalized)
    return normalized.strip()


def remove_residual_noise(text: str) -> str:
    if re.fullmatch(r"page\s+\d+", text, flags=re.IGNORECASE):
        return ""
    if re.fullmatch(r"[\-*_\s]{3,}", text):
        return ""
    return text


def merge_fragments(paragraphs: list[str]) -> list[str]:
    merged: list[str] = []
    for paragraph in paragraphs:
        if not merged:
            merged.append(paragraph)
            continue
        previous = merged[-1]
        if not re.search(r"[.!?\"')\]]$", previous) and paragraph[:1].islower():
            merged[-1] = f"{previous} {paragraph}"
        else:
            merged.append(paragraph)
    return merged
