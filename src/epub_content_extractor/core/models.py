from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import TypeAlias

FeatureValue: TypeAlias = bool | int | float | str


class BlockDecision(str, Enum):
    KEEP = "keep"
    MAYBE = "maybe"
    DROP = "drop"


@dataclass(slots=True)
class ExtractorConfig:
    min_chars: int = 25
    min_alpha_ratio: float = 0.6
    max_digit_ratio: float = 0.3
    keep_score: float = 0.3
    drop_score: float = 0.0


@dataclass(slots=True)
class TextBlock:
    text: str
    tag: str
    position: int
    chapter_index: int
    position_ratio: float = 0.0


@dataclass(frozen=True, slots=True)
class BlockFeatures:
    length_chars: int
    length_words: int
    avg_word_length: float
    punctuation_ratio: float
    alpha_ratio: float
    digit_ratio: float
    sentence_count: int
    is_uppercase: bool
    has_dialogue_markers: bool
    starts_with_number: bool
    ends_with_punctuation: bool
    repetition_score: float
    footnote_lines_ratio: float

    def as_feature_map(self) -> dict[str, FeatureValue]:
        values = asdict(self)
        return {
            key: value
            for key, value in values.items()
            if isinstance(value, bool | int | float | str)
        }


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    base_score: float
    penalty: float
    boost: float
    final_score: float
    hard_drop: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ClassifiedBlock:
    block: TextBlock
    features: BlockFeatures
    score: ScoreBreakdown
    decision: BlockDecision


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
    decision: BlockDecision
    score: ScoreBreakdown
    features: BlockFeatures

    def as_dict(self) -> dict[str, object]:
        return {
            "chapter_index": self.chapter_index,
            "position": self.position,
            "tag": self.tag,
            "text": self.text,
            "decision": self.decision.value,
            "score": asdict(self.score),
            "features": self.features.as_feature_map(),
        }


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

    def debug_as_dicts(self) -> list[dict[str, object]]:
        return [block.as_dict() for block in self.debug_blocks]
