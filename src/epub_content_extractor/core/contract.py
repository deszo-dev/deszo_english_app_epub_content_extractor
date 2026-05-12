from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .models import BlockDecision, ExtractedDocument

SCHEMA_VERSION = "epub_content_extractor.v1"

DiagnosticSeverity = Literal["info", "warning", "error"]


@dataclass(frozen=True, slots=True)
class CleanTextChapter:
    chapter_index: int
    title: str | None
    text_start_char: int
    text_end_char: int

    def to_dict(self) -> dict[str, object]:
        return {
            "chapter_index": self.chapter_index,
            "title": self.title,
            "text_start_char": self.text_start_char,
            "text_end_char": self.text_end_char,
        }


@dataclass(frozen=True, slots=True)
class CleanTextParagraph:
    paragraph_index: int
    chapter_index: int
    text: str
    text_start_char: int
    text_end_char: int

    def to_dict(self) -> dict[str, object]:
        return {
            "paragraph_index": self.paragraph_index,
            "chapter_index": self.chapter_index,
            "text": self.text,
            "text_start_char": self.text_start_char,
            "text_end_char": self.text_end_char,
        }


@dataclass(frozen=True, slots=True)
class EpubSourceMetadata:
    input_file_name: str | None = None
    input_sha256: str | None = None
    title: str | None = None
    author: str | None = None
    language: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "input_file_name": self.input_file_name,
            "input_sha256": self.input_sha256,
            "title": self.title,
            "author": self.author,
            "language": self.language,
        }


@dataclass(frozen=True, slots=True)
class EpubExtractionSummary:
    raw_block_count: int
    kept_block_count: int
    dropped_block_count: int
    maybe_block_count: int
    footnote_block_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "raw_block_count": self.raw_block_count,
            "kept_block_count": self.kept_block_count,
            "dropped_block_count": self.dropped_block_count,
            "maybe_block_count": self.maybe_block_count,
            "footnote_block_count": self.footnote_block_count,
        }


@dataclass(frozen=True, slots=True)
class EpubExtractionDiagnostic:
    code: str
    severity: DiagnosticSeverity
    message: str
    chapter_index: int | None = None
    block_index: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "chapter_index": self.chapter_index,
            "block_index": self.block_index,
        }


@dataclass(frozen=True, slots=True)
class CleanTextDocument:
    schema_version: str
    text: str
    chapters: list[CleanTextChapter]
    paragraphs: list[CleanTextParagraph]
    source: EpubSourceMetadata
    extraction_summary: EpubExtractionSummary
    diagnostics: list[EpubExtractionDiagnostic] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "text": self.text,
            "chapters": [chapter.to_dict() for chapter in self.chapters],
            "paragraphs": [paragraph.to_dict() for paragraph in self.paragraphs],
            "source": self.source.to_dict(),
            "extraction_summary": self.extraction_summary.to_dict(),
            "diagnostics": [diag.to_dict() for diag in self.diagnostics],
        }

    def to_minimal_dict(self) -> dict[str, str]:
        return {"text": self.text}


def summarize(document: ExtractedDocument) -> EpubExtractionSummary:
    raw = len(document.debug_blocks)
    kept = 0
    dropped = 0
    maybe = 0
    footnote = 0
    for info in document.debug_blocks:
        if info.decision is BlockDecision.KEEP:
            kept += 1
        elif info.decision is BlockDecision.MAYBE:
            maybe += 1
        else:
            dropped += 1
        if (
            "footnote_block" in info.score.reasons
            or "indexed_footnote_block" in info.score.reasons
        ):
            footnote += 1
    return EpubExtractionSummary(
        raw_block_count=raw,
        kept_block_count=kept,
        dropped_block_count=dropped,
        maybe_block_count=maybe,
        footnote_block_count=footnote,
    )


def build_clean_text_document(
    document: ExtractedDocument,
    source: EpubSourceMetadata,
    diagnostics: list[EpubExtractionDiagnostic] | None = None,
) -> CleanTextDocument:
    chapters: list[CleanTextChapter] = []
    paragraphs: list[CleanTextParagraph] = []
    text_parts: list[str] = []
    cursor = 0
    paragraph_index = 0

    rendered_chapters = [
        chapter for chapter in document.chapters if chapter.paragraphs
    ]

    for chapter_position, chapter in enumerate(rendered_chapters):
        if chapter_position > 0:
            text_parts.append("\n\n\n")
            cursor += 3
        chapter_start = cursor
        for para_position, paragraph in enumerate(chapter.paragraphs):
            if para_position > 0:
                text_parts.append("\n\n")
                cursor += 2
            para_start = cursor
            text_parts.append(paragraph)
            cursor += len(paragraph)
            paragraphs.append(
                CleanTextParagraph(
                    paragraph_index=paragraph_index,
                    chapter_index=chapter.chapter_index,
                    text=paragraph,
                    text_start_char=para_start,
                    text_end_char=cursor,
                )
            )
            paragraph_index += 1
        chapters.append(
            CleanTextChapter(
                chapter_index=chapter.chapter_index,
                title=chapter.title or None,
                text_start_char=chapter_start,
                text_end_char=cursor,
            )
        )

    return CleanTextDocument(
        schema_version=SCHEMA_VERSION,
        text="".join(text_parts),
        chapters=chapters,
        paragraphs=paragraphs,
        source=source,
        extraction_summary=summarize(document),
        diagnostics=list(diagnostics or []),
    )
