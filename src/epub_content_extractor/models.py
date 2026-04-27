from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Chapter:
    title: str
    paragraphs: list[str]


@dataclass(slots=True)
class BlockDebugInfo:
    chapter_index: int
    position: int
    tag: str
    text: str
    score: float
    keep: bool
    reasons: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExtractedDocument:
    chapters: list[Chapter]
    debug_blocks: list[BlockDebugInfo] = field(default_factory=list)

    def to_text(self) -> str:
        chapter_texts: list[str] = []
        for chapter in self.chapters:
            if chapter.paragraphs:
                chapter_texts.append("\n\n".join(chapter.paragraphs))
        return "\n\n\n".join(chapter_texts).strip()

    def debug_as_dicts(self) -> list[dict[str, Any]]:
        return [asdict(block) for block in self.debug_blocks]
