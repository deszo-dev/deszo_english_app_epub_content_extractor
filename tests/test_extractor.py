from __future__ import annotations

from pathlib import Path

from epub_content_extractor.adapters.epub import (
    is_gutenberg_boilerplate_document,
    strip_gutenberg_boilerplate_sections,
)
from epub_content_extractor.adapters.html import html_to_blocks
from epub_content_extractor.cli import main
from epub_content_extractor.core.footnotes import (
    build_footnote_index,
    remove_inline_footnote_markers,
)
from epub_content_extractor.core.models import BlockDecision, ExtractorConfig
from epub_content_extractor.core.pipeline import transform_blocks
from epub_content_extractor.core.scoring import classify_blocks
from epub_content_extractor.extractor import EpubContentExtractorPipeline
from epub_content_extractor.runtime_metadata import (
    canonical_json,
    source_fingerprint_for_paths,
    stage_fingerprint,
)


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


def test_gutenberg_header_section_does_not_drop_document_body() -> None:
    html = (
        '<html><body><div class="pg-boilerplate pgheader section">'
        "The Project Gutenberg eBook of A Book. "
        "*** START OF THE PROJECT GUTENBERG EBOOK A BOOK ***"
        "</div>"
        "<p>This is the real first paragraph of the story.</p></body></html>"
    )

    stripped = strip_gutenberg_boilerplate_sections(html)

    assert not is_gutenberg_boilerplate_document(stripped)
    assert html_to_blocks(stripped, 0)[0].text == (
        "This is the real first paragraph of the story."
    )


def test_cli_validation_error_uses_expected_exit_code(tmp_path: Path) -> None:
    input_path = tmp_path / "book.txt"
    input_path.write_text("not an epub", encoding="utf-8")

    assert main([str(input_path)]) == 1


def test_pipeline_exposes_runtime_metadata() -> None:
    metadata = EpubContentExtractorPipeline().runtime_metadata()

    assert metadata.stages
    assert set(metadata.stages) == {
        "content_extraction",
        "epub_document_reading",
        "html_block_extraction",
    }
    for stage_name, stage_metadata in metadata.stages.items():
        assert stage_metadata.stage_name == stage_name
        assert stage_metadata.stage_contract_version
        assert stage_metadata.output_schema_version
        assert stage_metadata.config_contract_version
        assert stage_metadata.module_version
        assert stage_metadata.source_fingerprint is not None
        assert stage_metadata.source_fingerprint.startswith("tree-sha256:")


def test_runtime_metadata_is_deterministic() -> None:
    pipeline = EpubContentExtractorPipeline()

    first = canonical_json(pipeline.runtime_metadata())
    second = canonical_json(pipeline.runtime_metadata())

    assert first == second


def test_runtime_dependencies_are_explicit() -> None:
    metadata = EpubContentExtractorPipeline().runtime_metadata()

    for stage in metadata.stages.values():
        for dependency in stage.dependencies:
            assert dependency.name
            assert dependency.version
            assert dependency.source == "package"
            assert dependency.compatibility == "exact"


def test_stage_fingerprint_changes_with_config_hash() -> None:
    metadata = EpubContentExtractorPipeline().runtime_metadata()
    stage = metadata.stages["content_extraction"]

    first = stage_fingerprint(
        stage,
        pipeline_contract_version=metadata.pipeline_contract_version,
        normalized_stage_config_hash="sha256:one",
        input_artifact_hashes={"blocks.json": "sha256:blocks"},
    )
    second = stage_fingerprint(
        stage,
        pipeline_contract_version=metadata.pipeline_contract_version,
        normalized_stage_config_hash="sha256:two",
        input_artifact_hashes={"blocks.json": "sha256:blocks"},
    )

    assert first != second


def test_source_fingerprint_changes_when_relevant_source_changes(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "stage.py"
    source_file.write_text("VALUE = 1\n", encoding="utf-8")
    first = source_fingerprint_for_paths(tmp_path, [source_file])

    source_file.write_text("VALUE = 2\n", encoding="utf-8")
    second = source_fingerprint_for_paths(tmp_path, [source_file])

    assert first != second
