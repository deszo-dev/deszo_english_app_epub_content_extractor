from __future__ import annotations

import json
from pathlib import Path

from epub_content_extractor.adapters.html import html_to_blocks
from epub_content_extractor.cli import main
from epub_content_extractor.core.contract import (
    SCHEMA_VERSION,
    EpubSourceMetadata,
    build_clean_text_document,
)
from epub_content_extractor.core.footnotes import (
    build_footnote_index,
    remove_inline_footnote_markers,
)
from epub_content_extractor.core.models import BlockDecision, ExtractorConfig
from epub_content_extractor.core.pipeline import transform_blocks
from epub_content_extractor.core.scoring import classify_blocks


def test_html_to_blocks_preserves_paragraph_spacing() -> None:
    blocks = html_to_blocks(
        "<html><body><p>Hello <b>world</b>.</p><p>Next.</p></body></html>",
        0,
    )

    assert [block.text for block in blocks] == ["Hello world.", "Next."]


def test_transform_blocks_assembles_paragraphs_and_chapters() -> None:
    first = html_to_blocks(
        "<p>This is the first complete paragraph.</p><p>This is the second one.</p>",
        0,
    )
    second = html_to_blocks("<p>Another chapter starts here.</p>", 1)

    document = transform_blocks([first, second])

    assert document.to_text() == (
        "This is the first complete paragraph.\n\n"
        "This is the second one.\n\n\n"
        "Another chapter starts here."
    )


def test_inline_bracket_marker_removed_when_matching_footnote_exists() -> None:
    blocks = html_to_blocks(
        "<p>He was late[1] before answering.</p><p>[1] He missed the train.</p>",
        0,
    )
    blocks[1].position_ratio = 0.9
    footnote_index = build_footnote_index(blocks)

    text = remove_inline_footnote_markers(blocks[0].text, footnote_index, blocks)

    assert text == "He was late before answering."


def test_parenthesized_reference_is_kept_without_confidence() -> None:
    blocks = html_to_blocks("<p>As shown in Figure (1), the result is stable.</p>", 0)

    text = remove_inline_footnote_markers(blocks[0].text, {}, blocks)

    assert text == "As shown in Figure (1), the result is stable."


def test_scoring_returns_explicit_decisions() -> None:
    blocks = html_to_blocks(
        "<p>This block is long enough to be classified as readable text.</p>"
        "<p>1234567890 1234567890 1234567890</p>",
        0,
    )

    classified = classify_blocks(blocks, [], {}, ExtractorConfig())

    assert classified[0].decision is BlockDecision.KEEP
    assert classified[1].decision is BlockDecision.DROP


def test_cli_validation_error_uses_expected_exit_code(tmp_path: Path) -> None:
    input_path = tmp_path / "book.txt"
    input_path.write_text("not an epub", encoding="utf-8")

    assert main([str(input_path)]) == 1


def test_clean_text_document_offsets_match_text() -> None:
    first = html_to_blocks(
        "<p>This is the first complete paragraph.</p><p>This is the second one.</p>",
        0,
    )
    second = html_to_blocks("<p>Another chapter starts here.</p>", 1)

    extracted = transform_blocks([first, second])
    document = build_clean_text_document(
        extracted,
        EpubSourceMetadata(input_file_name="sample.epub"),
    )

    assert document.schema_version == SCHEMA_VERSION
    assert document.text == extracted.to_text()
    assert len(document.chapters) == 2
    assert len(document.paragraphs) == 3
    for paragraph in document.paragraphs:
        assert (
            document.text[paragraph.text_start_char : paragraph.text_end_char]
            == paragraph.text
        )
    for chapter in document.chapters:
        slice_ = document.text[chapter.text_start_char : chapter.text_end_char]
        assert slice_  # non-empty
        assert "\n\n\n" not in slice_

    summary = document.extraction_summary
    assert summary.raw_block_count == (
        summary.kept_block_count
        + summary.maybe_block_count
        + summary.dropped_block_count
    )
    assert document.source.input_file_name == "sample.epub"


def test_clean_text_document_minimal_dict_only_has_text() -> None:
    blocks = html_to_blocks("<p>This is a single readable paragraph.</p>", 0)
    extracted = transform_blocks([blocks])
    document = build_clean_text_document(extracted, EpubSourceMetadata())

    assert document.to_minimal_dict() == {"text": extracted.to_text()}


def test_clean_text_document_to_dict_is_json_serializable() -> None:
    blocks = html_to_blocks("<p>This is a single readable paragraph.</p>", 0)
    extracted = transform_blocks([blocks])
    document = build_clean_text_document(
        extracted, EpubSourceMetadata(title="X", author="Y", language="en")
    )

    payload = document.to_dict()
    encoded = json.dumps(payload, ensure_ascii=False)
    restored = json.loads(encoded)
    assert restored["schema_version"] == SCHEMA_VERSION
    assert restored["text"] == document.text
    assert restored["source"]["title"] == "X"
    assert isinstance(restored["paragraphs"], list)
    assert isinstance(restored["chapters"], list)
    assert isinstance(restored["diagnostics"], list)
