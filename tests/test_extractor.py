from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest
from ebooklib import epub
from jsonschema import Draft202012Validator

from epub_content_extractor import (
    EpubCanonicalTextBuildOptions,
    EpubContentExtractorPipeline,
    build_canonical_text,
    extract_epub_content,
)
from epub_content_extractor.cli import main
from epub_content_extractor.config import SCHEMA_VERSION, default_config_dict
from epub_content_extractor.extractor import reset_fault_injection, set_fault_injection
from epub_content_extractor.schema_utils import config_schema, diagnostic_registry, error_registry, result_schema


DOC_FIXTURES = (
    "success/minimal_valid",
    "success/complex_valid",
    "failure/plain_text_epub_extension",
    "failure/valid_zip_not_epub",
    "security/path_traversal",
    "config/unknown_field",
    "limits/no_readable_content",
)


@pytest.fixture(autouse=True)
def clear_fault_injection() -> None:
    reset_fault_injection()
    yield
    reset_fault_injection()


def test_extract_epub_content_returns_structured_success_result(tmp_path: Path) -> None:
    epub_path = build_minimal_epub(tmp_path / "minimal_valid.epub")

    result = extract_epub_content(epub_path)

    assert result["schema_version"] == SCHEMA_VERSION
    assert result["status"] == "succeeded"
    validate_against_schema(result, result_schema())
    assert build_canonical_text(result["book"]) == "Chapter 1\n\nHello world."


def test_registry_matches_result_schema() -> None:
    diag_codes = {
        entry["code"]: entry["severity"]
        for entry in diagnostic_registry()["diagnostics"]
    }
    error_codes = {entry["code"] for entry in error_registry()["errors"]}

    schema_defs = result_schema()["$defs"]
    schema_diag = {
        item["properties"]["code"]["const"]: item["properties"]["severity"]["const"]
        for item in schema_defs["EpubDiagnostic"]["allOf"][0]["oneOf"]
    }
    schema_errors = set(schema_defs["EpubExtractionError"]["properties"]["code"]["enum"])

    assert diag_codes == schema_diag
    assert error_codes == schema_errors


def test_pipeline_timeout_fault_injection(tmp_path: Path) -> None:
    epub_path = build_minimal_epub(tmp_path / "timeout.epub")
    set_fault_injection(pipeline_timeout=True)

    result = extract_epub_content(epub_path)

    assert result["status"] == "failed"
    assert result["error"]["code"] == "pipeline_timeout"
    validate_against_schema(result, result_schema())


def test_html_parse_timeout_fault_injection(tmp_path: Path) -> None:
    epub_path = build_minimal_epub(tmp_path / "parse_timeout.epub")
    set_fault_injection(html_parse_timeout_hrefs=frozenset({"chapter_1.xhtml"}))

    result = extract_epub_content(epub_path)

    assert result["status"] == "failed"
    assert result["error"]["code"] == "no_readable_content"
    assert result["diagnostics"][0]["code"] == "html_document_parse_timeout_skipped"
    assert result["diagnostics"][1]["code"] == "empty_readable_content"


def test_cli_extract_outputs_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    epub_path = build_minimal_epub(tmp_path / "cli.epub")

    exit_code = main(["extract", str(epub_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "succeeded"


def test_pipeline_runtime_metadata_is_exposed() -> None:
    metadata = EpubContentExtractorPipeline().runtime_metadata()

    assert metadata.pipeline_contract_version == "3.0"
    assert set(metadata.stages) == {
        "content_extraction",
        "epub_document_reading",
        "html_block_extraction",
    }


def test_canonical_text_options_toggle_chapter_titles(tmp_path: Path) -> None:
    epub_path = build_minimal_epub(tmp_path / "options.epub")
    result = extract_epub_content(epub_path)
    book = result["book"]

    with_titles = build_canonical_text(
        book,
        options=EpubCanonicalTextBuildOptions(include_chapter_titles=True),
    )
    without_titles = build_canonical_text(
        book,
        options=EpubCanonicalTextBuildOptions(include_chapter_titles=False),
    )

    assert with_titles.startswith("Chapter 1")
    assert not without_titles.startswith("Chapter 1")
    assert "Hello world." in without_titles


def test_chapter_output_has_no_paragraphs_field(tmp_path: Path) -> None:
    epub_path = build_minimal_epub(tmp_path / "no_paragraphs.epub")
    result = extract_epub_content(epub_path)

    for chapter in result["book"]["chapters"]:
        assert "paragraphs" not in chapter
        assert isinstance(chapter["text"], str)


def test_config_schema_rejects_unknown_field() -> None:
    validator = Draft202012Validator(config_schema())
    errors = list(validator.iter_errors({"unknown": True}))

    assert errors


@pytest.mark.parametrize("fixture_rel", DOC_FIXTURES)
def test_doc_goldens(tmp_path: Path, fixture_rel: str) -> None:
    fixture_dir = Path("docs/testing/tests/fixtures/epub_content_extractor") / fixture_rel
    expected = load_json(fixture_dir / "expected.normalized.json")
    config = load_json(fixture_dir / "config.json")
    input_path = build_fixture_input(tmp_path, fixture_rel)

    overrides = expected_source_file_overrides(expected)
    if overrides:
        set_fault_injection(source_file_overrides=overrides)

    if fixture_rel == "config/unknown_field":
        result = extract_epub_content(input_path, config=config)
    else:
        result = extract_epub_content(input_path, config=config)

    normalized = normalize_result_for_snapshot(result)
    validate_against_schema(normalized, result_schema())
    assert normalized == expected


def build_fixture_input(tmp_path: Path, fixture_rel: str) -> Path:
    if fixture_rel == "success/minimal_valid":
        return build_minimal_epub(tmp_path / "minimal_valid.epub")
    if fixture_rel == "success/complex_valid":
        return build_complex_epub(tmp_path / "complex_valid.epub")
    if fixture_rel == "failure/plain_text_epub_extension":
        path = tmp_path / "plain_text_epub_extension.epub"
        path.write_text("plain text", encoding="utf-8")
        return path
    if fixture_rel == "failure/valid_zip_not_epub":
        path = tmp_path / "valid_zip_not_epub.epub"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("content.txt", "hello")
        return path
    if fixture_rel == "security/path_traversal":
        path = tmp_path / "path_traversal.epub"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("../evil.txt", "bad")
        return path
    if fixture_rel == "config/unknown_field":
        return tmp_path / "missing.epub"
    if fixture_rel == "limits/no_readable_content":
        return build_no_readable_content_epub(tmp_path / "no_readable_content.epub")
    raise AssertionError(f"unsupported fixture {fixture_rel}")


def build_minimal_epub(path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("urn:uuid:00000000-0000-4000-8000-000000000001")
    book.set_title("Minimal Valid EPUB")
    book.set_language("en")
    book.add_author("Jane Example")

    chapter = epub.EpubHtml(title="Chapter 1", file_name="chapter_1.xhtml", lang="en")
    chapter.content = "<h1>Chapter 1</h1><p>Hello world.</p>"
    book.add_item(chapter)
    book.toc = (epub.Link("chapter_1.xhtml", "Chapter 1", "chapter-1"),)
    book.spine = ["nav", chapter]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(path), book)
    remove_opf_modified(path)
    return path


def build_complex_epub(path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("9780000000002")
    book.set_title("Complex Valid EPUB")
    book.set_language("en")
    book.add_author("Jane Example")
    book.add_metadata("DC", "publisher", "Deszo Test Press")
    book.add_metadata("DC", "date", "2020-01-02")
    book.add_metadata("OPF", "meta", "2020-01-03T00:00:00Z", {"property": "dcterms:modified"})
    book.add_metadata("DC", "description", "A deterministic EPUB fixture for contract testing.")
    book.add_metadata("DC", "rights", "Public domain test fixture.")
    book.add_metadata("DC", "subject", "Testing")
    book.add_metadata("DC", "subject", "Fiction")
    book.add_metadata("OPF", "meta", "A Contract Fixture", {"name": "subtitle"})

    title_page = epub.EpubHtml(title="Title Page", file_name="title.xhtml", lang="en")
    title_page.content = "<h1>Title Page</h1><p>Complex Valid EPUB</p><p>Jane Example</p>"

    chapter_one = epub.EpubHtml(title="Chapter 1", file_name="chapter_1.xhtml", lang="en")
    chapter_one.content = (
        "<h1>Chapter 1</h1>"
        "<p>The first paragraph introduces the test book.[1]</p>"
        "<p>The second paragraph keeps stable ordering.</p>"
        "<p>[1] A short explanatory note.</p>"
    )

    chapter_two = epub.EpubHtml(title="Chapter 2", file_name="chapter_2.xhtml", lang="en")
    chapter_two.content = "<h1>Chapter 2</h1><p>A second chapter provides another body paragraph.</p>"

    notes = epub.EpubHtml(title="Notes", file_name="notes.xhtml", lang="en")
    notes.content = "<h1>Notes</h1><p>End notes for the test edition.</p>"

    cover = epub.EpubItem(
        uid="cover-image",
        file_name="images/cover.png",
        media_type="image/png",
        content=b"png",
    )

    for item in [title_page, chapter_one, chapter_two, notes, cover]:
        book.add_item(item)

    book.toc = (
        epub.Link("title.xhtml", "Title Page", "title-page"),
        epub.Link("chapter_1.xhtml", "Chapter 1", "chapter-1"),
        epub.Link("chapter_2.xhtml", "Chapter 2", "chapter-2"),
        epub.Link("notes.xhtml", "Notes", "notes"),
    )
    book.spine = ["nav", title_page, chapter_one, chapter_two, notes]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(path), book)
    rewrite_opf_modified(path, "2020-01-03T00:00:00Z")
    return path


def build_no_readable_content_epub(path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("urn:uuid:00000000-0000-4000-8000-000000000099")
    book.set_title("No Readable Content")
    book.set_language("en")
    book.add_author("Jane Example")

    chapter = epub.EpubHtml(title="Chapter 1", file_name="chapter_1.xhtml", lang="en")
    chapter.content = "<h1>Chapter 1</h1><p>[1] Only note content.</p>"
    book.add_item(chapter)
    book.toc = (epub.Link("chapter_1.xhtml", "Chapter 1", "chapter-1"),)
    book.spine = ["nav", chapter]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(path), book)
    remove_opf_modified(path)
    return path


def expected_source_file_overrides(expected: dict[str, object]) -> dict[str, dict[str, object]] | None:
    if expected["status"] != "succeeded":
        return None
    source = expected["book"]["metadata"]["source_file"]
    return {
        source["file_name"]: {
            "sha256": source["sha256"],
            "size_bytes": source["size_bytes"],
        }
    }


def normalize_result_for_snapshot(result: dict[str, object]) -> dict[str, object]:
    normalized = json.loads(json.dumps(result))
    normalized["extraction"]["started_at"] = "1970-01-01T00:00:00Z"
    normalized["extraction"]["finished_at"] = "1970-01-01T00:00:00Z"
    normalized["extraction"]["duration_ms"] = 0
    return normalized


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_against_schema(result: dict[str, object], schema: dict[str, object]) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(result), key=lambda item: list(item.path))
    assert not errors, errors[0].message if errors else ""


def rewrite_opf_modified(epub_path: Path, value: str) -> None:
    with zipfile.ZipFile(epub_path, "r") as archive:
        contents = {info.filename: archive.read(info.filename) for info in archive.infolist()}
    opf_name = next(name for name in contents if name.endswith(".opf"))
    text = contents[opf_name].decode("utf-8")
    text = re.sub(
        r'(<meta property="dcterms:modified">)[^<]+(</meta>)',
        rf"\g<1>{value}\g<2>",
        text,
        count=1,
    )
    contents[opf_name] = text.encode("utf-8")
    with zipfile.ZipFile(epub_path, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)


def remove_opf_modified(epub_path: Path) -> None:
    with zipfile.ZipFile(epub_path, "r") as archive:
        contents = {info.filename: archive.read(info.filename) for info in archive.infolist()}
    opf_name = next(name for name in contents if name.endswith(".opf"))
    text = contents[opf_name].decode("utf-8")
    text = re.sub(r'<meta property="dcterms:modified">[^<]+</meta>', "", text, count=1)
    contents[opf_name] = text.encode("utf-8")
    with zipfile.ZipFile(epub_path, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
