from __future__ import annotations

from collections.abc import Sequence

from epub_content_extractor.exceptions import PipelineInvariantError

from .footnotes import build_footnote_index, remove_inline_footnote_markers
from .models import (
    BlockDebugInfo,
    BlockDecision,
    Chapter,
    ExtractedDocument,
    ExtractorConfig,
    TextBlock,
)
from .scoring import apply_context, classify_blocks
from .text import merge_fragments, normalize_text, remove_residual_noise


def transform_blocks(
    chapters: Sequence[list[TextBlock]],
    config: ExtractorConfig | None = None,
) -> ExtractedDocument:
    resolved_config = config or ExtractorConfig()
    output_chapters: list[Chapter] = []
    debug_blocks: list[BlockDebugInfo] = []
    seen_texts: list[str] = []

    for chapter_blocks in chapters:
        if not chapter_blocks:
            continue
        footnote_index = build_footnote_index(chapter_blocks)
        classified = classify_blocks(
            chapter_blocks,
            seen_texts,
            footnote_index,
            resolved_config,
        )
        classified = apply_context(classified, resolved_config)

        paragraphs: list[str] = []
        for item in classified:
            text = remove_inline_footnote_markers(
                item.block.text,
                footnote_index,
                chapter_blocks,
            )
            text = remove_residual_noise(text)
            text = normalize_text(text)
            if item.decision is not BlockDecision.DROP and text:
                paragraphs.append(text)

            debug_blocks.append(
                BlockDebugInfo(
                    chapter_index=item.block.chapter_index,
                    position=item.block.position,
                    tag=item.block.tag,
                    text=item.block.text,
                    decision=item.decision,
                    score=item.score,
                    features=item.features,
                )
            )

        paragraphs = merge_fragments(paragraphs)
        if paragraphs:
            output_chapters.append(Chapter(title="", paragraphs=paragraphs))

        seen_texts.extend(item.block.text for item in classified)

    document = ExtractedDocument(chapters=output_chapters, debug_blocks=debug_blocks)
    validate_document(document)
    return document


def validate_document(document: ExtractedDocument) -> None:
    for chapter in document.chapters:
        for paragraph in chapter.paragraphs:
            if not paragraph.strip():
                raise PipelineInvariantError("empty paragraph passed post-processing")
            if "  " in paragraph:
                raise PipelineInvariantError("paragraph contains repeated spaces")
