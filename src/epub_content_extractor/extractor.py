from __future__ import annotations

from pathlib import Path

from .adapters.debug import write_debug
from .adapters.epub import read_epub
from .adapters.html import html_to_blocks
from .core.contract import (
    CleanTextDocument,
    EpubExtractionDiagnostic,
    build_clean_text_document,
)
from .core.models import ExtractedDocument, ExtractorConfig
from .core.pipeline import transform_blocks


def extract_document(
    epub_path: str | Path,
    *,
    config: ExtractorConfig | None = None,
    debug_dir: str | Path | None = None,
) -> ExtractedDocument:
    book = read_epub(epub_path)
    chapters = [
        html_to_blocks(document.html, document.chapter_index)
        for document in book.documents
    ]
    extracted = transform_blocks(chapters, config=config)
    if debug_dir is not None:
        write_debug(debug_dir, extracted)
    return extracted


def extract_text_from_epub(
    epub_path: str | Path,
    *,
    config: ExtractorConfig | None = None,
    debug_dir: str | Path | None = None,
) -> str:
    return extract_document(epub_path, config=config, debug_dir=debug_dir).to_text()


def extract_clean_text_document(
    epub_path: str | Path,
    *,
    config: ExtractorConfig | None = None,
    debug_dir: str | Path | None = None,
) -> CleanTextDocument:
    book = read_epub(epub_path)
    chapters = [
        html_to_blocks(document.html, document.chapter_index)
        for document in book.documents
    ]
    extracted = transform_blocks(chapters, config=config)
    if debug_dir is not None:
        write_debug(debug_dir, extracted)

    diagnostics: list[EpubExtractionDiagnostic] = []
    if not book.documents:
        diagnostics.append(
            EpubExtractionDiagnostic(
                code="epub_no_content_chapters",
                severity="warning",
                message="EPUB contained no non-boilerplate content documents.",
            )
        )
    return build_clean_text_document(extracted, book.metadata, diagnostics)
