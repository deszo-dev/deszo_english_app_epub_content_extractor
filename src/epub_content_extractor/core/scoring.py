from __future__ import annotations

import re

from .constants import BOILERPLATE, HEADING_TAGS
from .features import extract_features
from .footnotes import is_footnote_block, is_probable_footnote_block
from .models import (
    BlockDecision,
    ClassifiedBlock,
    ExtractorConfig,
    ScoreBreakdown,
    TextBlock,
)


def classify_blocks(
    blocks: list[TextBlock],
    seen_texts: list[str],
    footnote_index: dict[str, str],
    config: ExtractorConfig,
) -> list[ClassifiedBlock]:
    return [
        classify_block(block, seen_texts, footnote_index, config) for block in blocks
    ]


def classify_block(
    block: TextBlock,
    seen_texts: list[str],
    footnote_index: dict[str, str],
    config: ExtractorConfig,
) -> ClassifiedBlock:
    features = extract_features(block, seen_texts)
    penalty = 0.0
    boost = 0.0
    reasons: list[str] = []
    hard_drop = False
    lower_text = block.text.lower()

    if block.tag in HEADING_TAGS:
        penalty += 1.0
        hard_drop = True
        reasons.append("heading_removed")
    if features.length_chars < config.min_chars:
        penalty += 0.5
        reasons.append("short_block")
    if features.has_dialogue_markers:
        boost += 0.4
        reasons.append("dialogue_preserved")
    if features.alpha_ratio < config.min_alpha_ratio:
        penalty += 0.7
        reasons.append("low_alpha_ratio")
    if features.digit_ratio > config.max_digit_ratio:
        penalty += 0.6
        reasons.append("digit_heavy")
    if features.repetition_score > 0.9:
        penalty += 1.0
        reasons.append("repeated_block")
    if looks_like_toc(block.text):
        penalty += 1.0
        hard_drop = True
        reasons.append("toc_like")
    if features.sentence_count == 0:
        penalty += 0.5
        reasons.append("no_sentence_punctuation")
    if features.length_chars > 80:
        boost += 0.3
        reasons.append("long_text_block")
    if features.is_uppercase and features.length_chars < 80:
        penalty += 0.6
        reasons.append("short_uppercase")
    if block.chapter_index == 0 and block.position < 10:
        penalty += 0.3
        reasons.append("front_matter_position")
    if any(pattern in lower_text for pattern in BOILERPLATE):
        penalty += 1.0
        hard_drop = True
        reasons.append("boilerplate")
    if is_chapter_heading(block.text):
        penalty += 1.0
        hard_drop = True
        reasons.append("chapter_heading_removed")
    if is_footnote_block(block, features):
        penalty += 1.2
        hard_drop = True
        reasons.append("footnote_block")
    if footnote_index and is_probable_footnote_block(block.text):
        penalty += 0.8
        hard_drop = True
        reasons.append("indexed_footnote_block")

    final_score = 1.0 - penalty + boost
    score = ScoreBreakdown(
        base_score=1.0,
        penalty=penalty,
        boost=boost,
        final_score=final_score,
        hard_drop=hard_drop,
        reasons=tuple(reasons),
    )
    return ClassifiedBlock(
        block=block,
        features=features,
        score=score,
        decision=decision_from_score(score, config),
    )


def decision_from_score(
    score: ScoreBreakdown,
    config: ExtractorConfig,
) -> BlockDecision:
    if score.hard_drop or score.final_score < config.drop_score:
        return BlockDecision.DROP
    if score.final_score < config.keep_score:
        return BlockDecision.MAYBE
    return BlockDecision.KEEP


def apply_context(
    classified_blocks: list[ClassifiedBlock],
    config: ExtractorConfig,
) -> list[ClassifiedBlock]:
    result: list[ClassifiedBlock] = []
    scores = [item.score.final_score for item in classified_blocks]
    for index, item in enumerate(classified_blocks):
        decision = item.decision
        reasons = item.score.reasons
        if decision is BlockDecision.DROP and not item.score.hard_drop:
            start = max(0, index - 2)
            end = min(len(classified_blocks), index + 3)
            neighbor_scores = scores[start:index] + scores[index + 1 : end]
            if (
                neighbor_scores
                and sum(neighbor_scores) / len(neighbor_scores) >= config.keep_score
            ):
                decision = BlockDecision.MAYBE
                reasons = (*reasons, "kept_by_neighbors")
        result.append(replace_decision(item, decision, reasons))
    return drop_weak_sections(result, config)


def drop_weak_sections(
    classified_blocks: list[ClassifiedBlock],
    config: ExtractorConfig,
) -> list[ClassifiedBlock]:
    result: list[ClassifiedBlock] = []
    weak_run = 0
    for item in classified_blocks:
        decision = item.decision
        reasons = item.score.reasons
        if item.score.final_score < config.drop_score:
            weak_run += 1
        else:
            weak_run = 0
        if weak_run >= 5:
            decision = BlockDecision.DROP
            reasons = (*reasons, "weak_section")
        result.append(replace_decision(item, decision, reasons))
    return result


def replace_decision(
    item: ClassifiedBlock,
    decision: BlockDecision,
    reasons: tuple[str, ...],
) -> ClassifiedBlock:
    score = ScoreBreakdown(
        base_score=item.score.base_score,
        penalty=item.score.penalty,
        boost=item.score.boost,
        final_score=item.score.final_score,
        hard_drop=item.score.hard_drop,
        reasons=reasons,
    )
    return ClassifiedBlock(item.block, item.features, score, decision)


def looks_like_toc(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        lines = [text.strip()]
    matches = 0
    for line in lines:
        if re.search(r"\.{3,}", line):
            matches += 1
        elif re.search(r"\b(chapter|part)\s+\d+", line, flags=re.IGNORECASE):
            matches += 1
    return len(lines) >= 3 and matches / len(lines) > 0.5


def is_chapter_heading(text: str) -> bool:
    return bool(
        re.fullmatch(
            r"\s*(chapter|part)\s+([ivxlcdm]+|\d+)\s*[:.\-]?\s*",
            text,
            flags=re.IGNORECASE,
        )
    )
