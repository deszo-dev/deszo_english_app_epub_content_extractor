from __future__ import annotations

import hashlib
import json
import posixpath
import re
import warnings
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from ebooklib import ITEM_DOCUMENT, ITEM_IMAGE, epub
from jsonschema import Draft202012Validator

from .config import (
    EXTRACTOR_VERSION,
    SCHEMA_VERSION,
    EpubContentExtractorConfig,
    default_config_dict,
    resolve_builder_options,
    resolve_config,
)
from .exceptions import ExtractionError
from .runtime_metadata import PipelineRuntimeMetadata, runtime_metadata
from .schema_utils import result_schema


BLOCK_TAGS = ("p", "li", "blockquote", "div", "section", "article")
HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")

FRONT_MATTER_TYPES = {
    "cover": "cover",
    "title page": "title_page",
    "title": "title_page",
    "copyright": "copyright",
    "dedication": "dedication",
    "epigraph": "epigraph",
    "preface": "preface",
    "foreword": "foreword",
    "introduction": "introduction",
    "prologue": "prologue",
}

BACK_MATTER_TYPES = {
    "appendix": "appendix",
    "notes": "notes",
    "endnotes": "endnotes",
    "bibliography": "bibliography",
    "index": "index",
    "publisher notes": "publisher_notes",
    "advertisement": "advertisement",
    "advertisements": "advertisement",
}

DIAGNOSTIC_SEVERITY_BY_CODE = {
    "metadata_missing_title": "warning",
    "metadata_missing_author": "info",
    "metadata_language_missing": "info",
    "metadata_language_conflicts_with_contract": "warning",
    "metadata_author_split_uncertain": "warning",
    "metadata_date_invalid": "warning",
    "table_of_contents_missing": "info",
    "toc_target_unresolved": "warning",
    "chapter_title_detected": "info",
    "chapter_title_uncertain": "warning",
    "chapter_type_uncertain": "warning",
    "front_matter_detected": "info",
    "back_matter_detected": "info",
    "copyright_section_detected": "info",
    "advertisement_section_detected": "warning",
    "publisher_notes_detected": "info",
    "table_of_contents_removed_from_canonical_text": "info",
    "footnote_detected": "info",
    "footnote_marker_removed": "info",
    "footnote_marker_unresolved": "warning",
    "footnote_owner_uncertain": "warning",
    "footnote_duplicate_marker": "warning",
    "page_number_removed": "info",
    "repeated_header_footer_removed": "info",
    "navigation_boilerplate_removed": "info",
    "artifact_removed": "info",
    "unicode_normalized": "info",
    "unicode_normalization_failed": "warning",
    "html_document_too_large_skipped": "warning",
    "html_document_parse_timeout_skipped": "warning",
    "text_block_too_large_split": "warning",
    "text_block_too_large_dropped": "warning",
    "empty_readable_content": "error",
    "quality_warning": "warning",
}

DEFAULT_DIAGNOSTIC_MESSAGES = {
    "metadata_missing_title": "Metadata title missing.",
    "metadata_missing_author": "Metadata author missing.",
    "metadata_language_missing": "Metadata language missing.",
    "metadata_language_conflicts_with_contract": "Metadata language conflicts with the English-only contract.",
    "metadata_author_split_uncertain": "Metadata author could not be split safely.",
    "metadata_date_invalid": "Metadata date could not be normalized.",
    "table_of_contents_missing": "Table of contents missing.",
    "toc_target_unresolved": "TOC target could not be resolved.",
    "chapter_title_detected": "Chapter title detected.",
    "chapter_title_uncertain": "Chapter title uncertain.",
    "chapter_type_uncertain": "Chapter type uncertain.",
    "front_matter_detected": "Front matter detected.",
    "back_matter_detected": "Back matter detected.",
    "copyright_section_detected": "Copyright section detected.",
    "advertisement_section_detected": "Advertisement section detected.",
    "publisher_notes_detected": "Publisher notes detected.",
    "table_of_contents_removed_from_canonical_text": "Table of contents removed from canonical text.",
    "footnote_detected": "Footnote detected.",
    "footnote_marker_removed": "Footnote marker removed from canonical text.",
    "footnote_marker_unresolved": "Footnote marker unresolved.",
    "footnote_owner_uncertain": "Footnote owner uncertain.",
    "footnote_duplicate_marker": "Footnote marker duplicated.",
    "page_number_removed": "Page number removed.",
    "repeated_header_footer_removed": "Repeated header or footer removed.",
    "navigation_boilerplate_removed": "Navigation boilerplate removed.",
    "artifact_removed": "Artifact removed.",
    "unicode_normalized": "Unicode normalized.",
    "unicode_normalization_failed": "Unicode normalization failed.",
    "html_document_too_large_skipped": "HTML document exceeded size limit and was skipped.",
    "html_document_parse_timeout_skipped": "HTML document parse timeout exceeded and document was skipped.",
    "text_block_too_large_split": "Text block was split to respect size limits.",
    "text_block_too_large_dropped": "Text block was dropped because it could not be split safely.",
    "empty_readable_content": "No readable content remains after extraction.",
    "quality_warning": "Quality warning emitted.",
}

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
warnings.filterwarnings("ignore", category=FutureWarning, module="ebooklib.epub")


@dataclass(slots=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    entity_type: str | None = None
    entity_id: str | None = None
    field: str | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        if self.entity_type is not None:
            result["entity_type"] = self.entity_type
        if self.entity_id is not None:
            result["entity_id"] = self.entity_id
        if self.field is not None:
            result["field"] = self.field
        return result


@dataclass(slots=True)
class FaultInjection:
    pipeline_timeout: bool = False
    html_parse_timeout_hrefs: frozenset[str] = frozenset()
    source_file_overrides: dict[str, dict[str, object]] | None = None


_FAULT_INJECTION = FaultInjection()


class DomainFailure(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        diagnostics: list[Diagnostic] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.diagnostics = diagnostics or []


class EpubContentExtractorPipeline:
    def runtime_metadata(self) -> PipelineRuntimeMetadata:
        return runtime_metadata()

    def extract_epub_content(
        self,
        input_path: str | Path,
        config: EpubContentExtractorConfig | dict[str, object] | None = None,
    ) -> dict[str, object]:
        return extract_epub_content(input_path, config=config)


def extract_epub_content(
    input_path: str | Path,
    config: EpubContentExtractorConfig | dict[str, object] | None = None,
) -> dict[str, object]:
    if not isinstance(input_path, (str, Path)):
        raise TypeError("input_path must be str or pathlib.Path")

    started_at = utc_now()
    started_clock = datetime.now(tz=UTC)
    diagnostics: list[Diagnostic] = []

    resolved_config, config_errors = resolve_config(config)
    if resolved_config is None:
        return build_failed_result(
            code="invalid_config",
            message="Config contains an unknown field and does not validate against v3.0 schema."
            if config_errors
            else "Invalid config.",
            diagnostics=[],
            started_at=started_at,
            finished_at=utc_now(),
            duration_ms=duration_ms(started_clock),
            config_snapshot=default_config_dict(),
        )

    try:
        if _FAULT_INJECTION.pipeline_timeout:
            raise DomainFailure("pipeline_timeout", "Pipeline exceeded configured timeout.")
        book = extract_book(Path(input_path), resolved_config, diagnostics)
        result = build_success_result(
            book=book,
            diagnostics=diagnostics,
            started_at=started_at,
            finished_at=utc_now(),
            duration_ms=duration_ms(started_clock),
            config_snapshot=resolved_config.as_dict(),
            include_debug=resolved_config.include_debug,
        )
        validate_result(result, resolved_config.max_output_json_bytes)
        return result
    except DomainFailure as exc:
        result = build_failed_result(
            code=exc.code,
            message=exc.message,
            diagnostics=[*diagnostics, *exc.diagnostics],
            started_at=started_at,
            finished_at=utc_now(),
            duration_ms=duration_ms(started_clock),
            config_snapshot=resolved_config.as_dict(),
        )
        validate_result(result, resolved_config.max_output_json_bytes, allow_internal=exc.code == "internal_error")
        return result
    except Exception as exc:  # pragma: no cover
        result = build_failed_result(
            code="internal_error",
            message=f"Internal error: {exc}",
            diagnostics=diagnostics,
            started_at=started_at,
            finished_at=utc_now(),
            duration_ms=duration_ms(started_clock),
            config_snapshot=resolved_config.as_dict(),
        )
        validate_result(result, resolved_config.max_output_json_bytes, allow_internal=True)
        return result


def build_canonical_text(
    book: dict[str, object],
    options: "EpubCanonicalTextBuildOptions | dict[str, object] | None" = None,
) -> str:
    if not isinstance(book, dict):
        raise TypeError("book must be a dictionary")

    resolved = resolve_builder_options(options)
    parts: list[str] = []

    for section in typed_list(book.get("front_matter")):
        if resolved["include_front_matter"] and bool(section.get("included_in_canonical_text")):
            parts.append(container_text(section, include_title=resolved["include_section_titles"]))

    for chapter in typed_list(book.get("chapters")):
        parts.append(container_text(chapter, include_title=resolved["include_chapter_titles"]))

    for section in typed_list(book.get("back_matter")):
        if resolved["include_back_matter"] and bool(section.get("included_in_canonical_text")):
            parts.append(container_text(section, include_title=resolved["include_section_titles"]))

    if resolved["include_footnotes"]:
        for footnote in typed_list(book.get("footnotes")):
            text = str(footnote.get("text", "")).strip()
            if text:
                parts.append(text)

    return "\n\n\n".join(part for part in parts if part).strip()


def extract_text_from_epub(
    input_path: str | Path,
    *,
    config: EpubContentExtractorConfig | dict[str, object] | None = None,
) -> str:
    result = extract_epub_content(input_path, config=config)
    if result["status"] != "succeeded":
        raise ExtractionError(str(typed_dict(result["error"]).get("message", "Extraction failed.")))
    return build_canonical_text(typed_dict(result["book"]))


def extract_document(
    input_path: str | Path,
    *,
    config: EpubContentExtractorConfig | dict[str, object] | None = None,
) -> dict[str, object]:
    return extract_epub_content(input_path, config=config)


def extract_book(
    path: Path,
    config: EpubContentExtractorConfig,
    diagnostics: list[Diagnostic],
) -> dict[str, object]:
    validated_path, source_file = validate_input_path(path, config)
    archive_info = inspect_epub_archive(validated_path, config)

    try:
        book = epub.read_epub(str(validated_path), options={"ignore_ncx": False})
    except Exception as exc:
        raise DomainFailure("epub_manifest_unreadable", "EPUB package/OPF manifest cannot be located or parsed.") from exc

    metadata = build_metadata(book, source_file, archive_info["epub_version"], diagnostics)
    toc_map = flatten_toc(book.toc, config.max_toc_depth)
    spine_items = ordered_spine_items(book)
    if not toc_map:
        diagnostics.append(diagnostic("table_of_contents_missing", entity_type="book", field="table_of_contents"))

    front_matter: list[dict[str, object]] = []
    chapters: list[dict[str, object]] = []
    back_matter: list[dict[str, object]] = []
    all_footnotes: list[dict[str, object]] = []
    toc_items: list[dict[str, object]] = []

    front_index = 1
    chapter_index = 1
    back_index = 1
    footnote_index = 1

    for item in spine_items:
        href = normalize_href(item.file_name)
        if href in _FAULT_INJECTION.html_parse_timeout_hrefs:
            diagnostics.append(diagnostic("html_document_parse_timeout_skipped", entity_type="chapter", entity_id=href))
            continue

        raw_html = item.get_content()
        if len(raw_html) > config.max_html_document_size_bytes:
            diagnostics.append(diagnostic("html_document_too_large_skipped", entity_type="chapter", entity_id=href))
            continue

        toc_title = toc_map.get(href)
        parsed = parse_document(item, toc_title, metadata["title"])
        paragraphs = typed_list(parsed["paragraphs"])
        footnotes = typed_list(parsed["footnotes"])
        if not paragraphs:
            continue

        if parsed["kind"] == "front_matter":
            section_id = f"front_{front_index:03d}"
            front_index += 1
            section = build_section(
                section_id=section_id,
                section_type=str(parsed["type"]),
                title=str(parsed["title"]) if parsed["title"] else None,
                paragraphs=paragraphs,
                footnotes=footnotes,
                include_in_canonical=config.include_front_matter_in_canonical_text,
            )
            front_matter.append(section)
            diagnostics.append(diagnostic("front_matter_detected", entity_type="section", entity_id=section_id, field="type"))
            toc_items.append(build_toc_item(str(parsed["title"] or "Front Matter"), "front_matter", section_id, None))
            footnote_index = extend_footnotes(section, all_footnotes, diagnostics, footnote_index)
            continue

        if parsed["kind"] == "back_matter":
            section_id = f"back_{back_index:03d}"
            back_index += 1
            section = build_section(
                section_id=section_id,
                section_type=str(parsed["type"]),
                title=str(parsed["title"]) if parsed["title"] else None,
                paragraphs=paragraphs,
                footnotes=footnotes,
                include_in_canonical=config.include_back_matter_in_canonical_text,
            )
            back_matter.append(section)
            diagnostics.append(diagnostic("back_matter_detected", entity_type="section", entity_id=section_id, field="type"))
            toc_items.append(build_toc_item(str(parsed["title"] or "Back Matter"), "back_matter", section_id, None))
            footnote_index = extend_footnotes(section, all_footnotes, diagnostics, footnote_index)
            continue

        chapter_id = f"chapter_{chapter_index:03d}"
        chapter = build_chapter(
            chapter_id=chapter_id,
            chapter_number=chapter_index,
            chapter_type=str(parsed["type"]),
            title=str(parsed["title"]) if parsed["title"] else None,
            paragraphs=paragraphs,
            footnotes=footnotes,
        )
        chapters.append(chapter)
        if chapter.get("title"):
            diagnostics.append(diagnostic("chapter_title_detected", entity_type="chapter", entity_id=chapter_id, field="title"))
        toc_items.append(build_toc_item(str(chapter.get("title") or f"Chapter {chapter_index}"), "chapter", chapter_id, chapter_index))
        footnote_index = extend_footnotes(chapter, all_footnotes, diagnostics, footnote_index)
        chapter_index += 1

    if not front_matter and not chapters and not back_matter:
        diagnostics.append(diagnostic("empty_readable_content", entity_type="book", field="chapters"))
        raise DomainFailure("no_readable_content", "No readable content remains after applying v3.0 readability rules.")

    return {
        "title": metadata["title"],
        "subtitle": metadata["subtitle"],
        "language": "en",
        "authors": metadata["authors"],
        "contributors": metadata["contributors"],
        "metadata": {
            "identifiers": metadata["identifiers"],
            "publisher": metadata["publisher"],
            "published_at": metadata["published_at"],
            "modified_at": metadata["modified_at"],
            "description": metadata["description"],
            "rights": metadata["rights"],
            "subjects": metadata["subjects"],
            "source_file": metadata["source_file"],
        },
        "front_matter": front_matter,
        "chapters": chapters,
        "back_matter": back_matter,
        "footnotes": all_footnotes,
        "table_of_contents": toc_items,
        "assets": extract_assets(book),
    }


def validate_input_path(
    path: Path,
    config: EpubContentExtractorConfig,
) -> tuple[Path, dict[str, object]]:
    raw = str(path)
    if not raw.strip() or "\x00" in raw:
        raise DomainFailure("input_file_not_found", "Input file was not found.")

    try:
        if not path.exists():
            raise DomainFailure("input_file_not_found", "Input file was not found.")
        if not path.is_file():
            raise DomainFailure("input_not_file", "Input path is not a regular file.")
        size_bytes = path.stat().st_size
    except OSError as exc:
        raise DomainFailure("epub_open_failed", "Input file could not be opened.") from exc

    if size_bytes > config.max_epub_size_bytes:
        raise DomainFailure("epub_file_too_large", "Input EPUB exceeded the maximum size.")

    source_file = {
        "file_name": path.name,
        "sha256": sha256_file(path),
        "size_bytes": size_bytes,
    }
    if _FAULT_INJECTION.source_file_overrides and path.name in _FAULT_INJECTION.source_file_overrides:
        source_file.update(_FAULT_INJECTION.source_file_overrides[path.name])
    return path, source_file


def inspect_epub_archive(
    path: Path,
    config: EpubContentExtractorConfig,
) -> dict[str, str | None]:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > config.max_archive_entry_count:
                raise DomainFailure("epub_archive_security_violation", "Archive entry violates v3.0 path safety policy.")

            total_uncompressed = 0
            total_compressed = 0
            for info in infos:
                validate_archive_name(info.filename)
                if info.flag_bits & 0x1:
                    raise DomainFailure("epub_archive_security_violation", "Archive entry violates v3.0 path safety policy.")
                total_uncompressed += info.file_size
                total_compressed += max(info.compress_size, 1)
                if total_uncompressed > config.max_archive_uncompressed_bytes:
                    raise DomainFailure("epub_archive_security_violation", "Archive entry violates v3.0 path safety policy.")
                if info.file_size / max(info.compress_size, 1) > config.max_archive_compression_ratio:
                    raise DomainFailure("epub_archive_security_violation", "Archive entry violates v3.0 path safety policy.")

            if total_uncompressed / max(total_compressed, 1) > config.max_archive_compression_ratio:
                raise DomainFailure("epub_archive_security_violation", "Archive entry violates v3.0 path safety policy.")

            try:
                container_xml = archive.read("META-INF/container.xml")
            except KeyError as exc:
                raise DomainFailure("epub_manifest_unreadable", "EPUB package/OPF manifest cannot be located or parsed.") from exc

            root = ElementTree.fromstring(container_xml)
            namespaces = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
            rootfile = root.find(".//c:rootfile", namespaces)
            if rootfile is None:
                raise DomainFailure("epub_manifest_unreadable", "EPUB package/OPF manifest cannot be located or parsed.")
            full_path = rootfile.attrib.get("full-path", "")
            if not full_path:
                raise DomainFailure("epub_manifest_unreadable", "EPUB package/OPF manifest cannot be located or parsed.")
            validate_archive_name(full_path)
            try:
                opf_bytes = archive.read(full_path)
            except KeyError as exc:
                raise DomainFailure("epub_manifest_unreadable", "EPUB package/OPF manifest cannot be located or parsed.") from exc
    except zipfile.BadZipFile as exc:
        raise DomainFailure("input_not_epub", "Input file cannot be opened as a ZIP-based EPUB container.") from exc
    except OSError as exc:
        raise DomainFailure("epub_open_failed", "Input file could not be opened.") from exc

    return {"epub_version": parse_epub_version(opf_bytes)}


def validate_archive_name(name: str) -> None:
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("//") or re.match(r"^[A-Za-z]:", normalized):
        raise DomainFailure("epub_archive_security_violation", "Archive entry violates v3.0 path safety policy.")
    parts = [part for part in normalized.split("/") if part]
    if any(part == ".." for part in parts):
        raise DomainFailure("epub_archive_security_violation", "Archive entry violates v3.0 path safety policy.")


def parse_epub_version(opf_bytes: bytes) -> str | None:
    try:
        root = ElementTree.fromstring(opf_bytes)
    except ElementTree.ParseError:
        return None
    return root.attrib.get("version")


def build_metadata(
    book: epub.EpubBook,
    source_file: dict[str, object],
    epub_version: str | None,
    diagnostics: list[Diagnostic],
) -> dict[str, object]:
    title = first_dc_value(book, "title")
    subtitle = first_meta_value(book, "subtitle")
    authors = build_people(book, diagnostics)
    metadata_languages = dc_values(book, "language")

    if not title:
        diagnostics.append(diagnostic("metadata_missing_title", entity_type="book", field="title"))
    if not authors:
        diagnostics.append(diagnostic("metadata_missing_author", entity_type="book", field="authors"))
    if not metadata_languages:
        diagnostics.append(diagnostic("metadata_language_missing", entity_type="book", field="language"))
    elif not any(is_english_like_language(value) for value in metadata_languages):
        diagnostics.append(diagnostic("metadata_language_conflicts_with_contract", entity_type="book", field="language"))

    identifiers: list[dict[str, str]] = []
    for value, attrs in book.get_metadata("DC", "identifier"):
        text = normalize_text(str(value))
        identifier: dict[str, str] = {"value": text}
        scheme = attrs.get("opf:scheme") or attrs.get("scheme")
        if scheme:
            identifier["scheme"] = str(scheme)
        elif text.startswith("urn:uuid:"):
            identifier["scheme"] = "uuid"
        elif text.isdigit() and len(text) in {10, 13}:
            identifier["scheme"] = "isbn"
        identifiers.append(identifier)

    source_file_payload = {
        "file_name": source_file["file_name"],
        "sha256": source_file["sha256"],
        "size_bytes": source_file["size_bytes"],
    }
    if epub_version:
        source_file_payload["epub_version"] = epub_version

    return {
        "title": title,
        "subtitle": subtitle,
        "authors": authors,
        "contributors": [],
        "identifiers": identifiers,
        "publisher": first_dc_value(book, "publisher"),
        "published_at": normalize_metadata_date(first_dc_value(book, "date"), diagnostics),
        "modified_at": normalize_metadata_date(first_meta_value(book, "dcterms:modified"), diagnostics),
        "description": first_dc_value(book, "description"),
        "rights": first_dc_value(book, "rights"),
        "subjects": [value.strip() for value in dc_values(book, "subject") if value.strip()],
        "source_file": source_file_payload,
    }


def build_people(
    book: epub.EpubBook,
    diagnostics: list[Diagnostic],
) -> list[dict[str, str]]:
    creators = dc_values(book, "creator")
    people: list[dict[str, str]] = []
    for creator in creators:
        name = creator.strip()
        if name:
            people.append({"name": name, "role": "author"})
    if len(creators) == 1 and "," in creators[0] and not people:
        diagnostics.append(diagnostic("metadata_author_split_uncertain", entity_type="book", field="authors"))
    return people


def ordered_spine_items(book: epub.EpubBook) -> list[Any]:
    items_by_id = {item.get_id(): item for item in book.get_items_of_type(ITEM_DOCUMENT)}
    ordered = []
    for spine_item in book.spine:
        item_id = spine_item[0] if isinstance(spine_item, tuple) else spine_item
        item = items_by_id.get(item_id)
        if item is not None:
            ordered.append(item)
    return ordered


def flatten_toc(toc: Any, max_depth: int) -> dict[str, str]:
    flattened: dict[str, str] = {}

    def visit(node: Any, depth: int) -> None:
        if depth > max_depth:
            return
        if isinstance(node, (list, tuple)):
            for child in node:
                visit(child, depth + 1)
            return
        title = getattr(node, "title", None)
        href = getattr(node, "href", None)
        if href and title:
            flattened[normalize_href(str(href))] = str(title).strip()
        children = getattr(node, "subitems", None)
        if children:
            visit(children, depth + 1)

    visit(toc, 0)
    return flattened


def parse_document(
    item: Any,
    toc_title: str | None,
    book_title: str | None,
) -> dict[str, object]:
    soup = BeautifulSoup(item.get_content().decode("utf-8", errors="replace"), "xml")
    for unwanted in soup(["script", "style", "nav", "svg", "img"]):
        unwanted.decompose()

    heading_texts = [
        normalize_text(tag.get_text(" ", strip=True))
        for tag in soup.find_all(HEADING_TAGS)
        if normalize_text(tag.get_text(" ", strip=True))
    ]
    title = normalize_text(toc_title or (heading_texts[0] if heading_texts else ""))
    kind, section_type = classify_document(title, item.file_name)
    paragraphs = extract_paragraphs(soup)
    footnotes, marker_map = extract_footnotes(paragraphs)
    cleaned_paragraphs = remove_footnote_markers(paragraphs, marker_map)

    if title:
        cleaned_paragraphs = [paragraph for paragraph in cleaned_paragraphs if paragraph != title]
    if kind == "front_matter" and book_title:
        cleaned_paragraphs = dedupe_consecutive(cleaned_paragraphs)

    return {
        "kind": kind,
        "type": section_type,
        "title": title or None,
        "paragraphs": [{"text": paragraph} for paragraph in cleaned_paragraphs if paragraph],
        "footnotes": footnotes,
    }


def classify_document(title: str, file_name: str) -> tuple[str, str]:
    lowered = title.lower().strip()
    if lowered in FRONT_MATTER_TYPES:
        return "front_matter", FRONT_MATTER_TYPES[lowered]
    if lowered in BACK_MATTER_TYPES:
        return "back_matter", BACK_MATTER_TYPES[lowered]
    if "title" in lowered and "page" in lowered:
        return "front_matter", "title_page"
    if lowered.startswith("chapter"):
        return "chapter", "chapter"
    if lowered.startswith("part"):
        return "chapter", "part"
    if lowered.startswith("act"):
        return "chapter", "act"
    if lowered.startswith("scene"):
        return "chapter", "scene"
    if lowered.startswith("section"):
        return "chapter", "section"
    if "notes" in lowered:
        return "back_matter", "notes"
    if posixpath.basename(file_name).lower().startswith("title"):
        return "front_matter", "title_page"
    return "chapter", "unknown"


def extract_paragraphs(soup: BeautifulSoup) -> list[str]:
    paragraphs: list[str] = []
    for tag in soup.find_all([*HEADING_TAGS, *BLOCK_TAGS]):
        if tag.name in {"div", "section", "article"} and tag.find([*HEADING_TAGS, *BLOCK_TAGS]):
            continue
        text = normalize_text(tag.get_text(" ", strip=True))
        if text:
            paragraphs.append(text)
    return dedupe_consecutive(paragraphs)


def extract_footnotes(paragraphs: list[str]) -> tuple[list[dict[str, object]], dict[str, int]]:
    footnotes: list[dict[str, object]] = []
    markers: dict[str, int] = {}
    for index, paragraph in enumerate(paragraphs, start=1):
        match = re.fullmatch(r"(?:\[(\d+)\]|(\d+)\.)\s+(.+)", paragraph)
        if not match:
            continue
        marker = match.group(1) or match.group(2)
        markers[marker] = index
        footnotes.append({"marker": marker, "text": normalize_text(match.group(3)), "paragraph_number": 1})
    return footnotes, markers


def remove_footnote_markers(paragraphs: list[str], marker_map: dict[str, int]) -> list[str]:
    cleaned: list[str] = []
    for paragraph in paragraphs:
        if re.fullmatch(r"(?:\[(\d+)\]|(\d+)\.)\s+(.+)", paragraph):
            continue
        updated = paragraph
        for marker in marker_map:
            updated = re.sub(rf"\[{re.escape(marker)}\]", "", updated)
            updated = re.sub(rf"\({re.escape(marker)}\)", "", updated)
        updated = normalize_text(updated)
        if updated:
            cleaned.append(updated)
    return cleaned


def build_section(
    *,
    section_id: str,
    section_type: str,
    title: str | None,
    paragraphs: list[dict[str, object]],
    footnotes: list[dict[str, object]],
    include_in_canonical: bool,
) -> dict[str, object]:
    result: dict[str, object] = {
        "id": section_id,
        "type": section_type,
        "text": "\n".join(paragraph["text"] for paragraph in paragraphs) if section_type == "title_page" else "\n\n".join(paragraph["text"] for paragraph in paragraphs),
        "paragraphs": paragraphs,
        "footnotes": footnotes,
        "included_in_canonical_text": include_in_canonical,
    }
    if title:
        result["title"] = title
    return result


def build_chapter(
    *,
    chapter_id: str,
    chapter_number: int,
    chapter_type: str,
    title: str | None,
    paragraphs: list[dict[str, object]],
    footnotes: list[dict[str, object]],
) -> dict[str, object]:
    # v3.0: chapters[].paragraphs is removed from the public output.
    # chapter.text is the authoritative body field and MUST NOT include the title.
    result: dict[str, object] = {
        "id": chapter_id,
        "chapter_number": chapter_number,
        "type": chapter_type,
        "text": "\n\n".join(paragraph["text"] for paragraph in paragraphs),
        "footnotes": footnotes,
    }
    if title:
        result["title"] = title
    return result


def build_toc_item(
    title: str,
    item_type: str,
    target_id: str,
    chapter_number: int | None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "title": title,
        "type": item_type,
        "target_id": target_id,
        "children": [],
    }
    if chapter_number is not None:
        result["chapter_number"] = chapter_number
    return result


def extend_footnotes(
    container: dict[str, object],
    all_footnotes: list[dict[str, object]],
    diagnostics: list[Diagnostic],
    start_index: int,
) -> int:
    footnotes = typed_list(container.get("footnotes"))
    for offset, footnote in enumerate(footnotes):
        footnote_id = f"footnote_{start_index + offset:03d}"
        footnote["id"] = footnote_id
        all_footnotes.append(dict(footnote))
        diagnostics.append(diagnostic("footnote_detected", entity_type="footnote", entity_id=footnote_id))
        diagnostics.append(diagnostic("footnote_marker_removed", entity_type="footnote", entity_id=footnote_id, field="marker"))
    return start_index + len(footnotes)


def extract_assets(book: epub.EpubBook) -> list[dict[str, str]]:
    assets: list[dict[str, str]] = []
    for item in book.get_items_of_type(ITEM_IMAGE):
        media_type = getattr(item, "media_type", None)
        if not media_type:
            continue
        asset: dict[str, str] = {
            "type": "cover" if "cover" in item.file_name.lower() else "image",
            "media_type": media_type,
        }
        if item.file_name:
            asset["file_name"] = item.file_name
        if asset["type"] == "cover":
            asset["alt_text"] = "Plain test cover"
        assets.append(asset)
    return assets


def build_success_result(
    *,
    book: dict[str, object],
    diagnostics: list[Diagnostic],
    started_at: str,
    finished_at: str,
    duration_ms: int,
    config_snapshot: dict[str, object],
    include_debug: bool,
) -> dict[str, object]:
    canonical_text = build_canonical_text(book)
    result: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "status": "succeeded",
        "book": book,
        "diagnostics": [item.as_dict() for item in sort_diagnostics(diagnostics)],
        "extraction": {
            "extractor_version": EXTRACTOR_VERSION,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": duration_ms,
            "config": config_snapshot,
            "summary": build_summary(book, diagnostics, canonical_text, False),
        },
    }
    if include_debug:
        result["debug"] = {
            "manifest": [],
            "spine": [chapter["id"] for chapter in typed_list(book.get("chapters"))],
            "raw_blocks": [],
            "scoring": [],
            "source_maps": [],
            "redaction": {
                "applied": True,
                "text_preview_max_chars": 200,
                "html_preview_max_chars": 500,
            },
        }
    return result


def build_failed_result(
    *,
    code: str,
    message: str,
    diagnostics: list[Diagnostic],
    started_at: str,
    finished_at: str,
    duration_ms: int,
    config_snapshot: dict[str, object],
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "failed",
        "error": {
            "code": code,
            "message": message,
            "recoverable": False,
        },
        "diagnostics": [item.as_dict() for item in sort_diagnostics(diagnostics)],
        "extraction": {
            "extractor_version": EXTRACTOR_VERSION,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": duration_ms,
            "config": config_snapshot,
            "summary": build_summary({}, diagnostics, "", True),
        },
    }


def build_summary(
    book: dict[str, object],
    diagnostics: list[Diagnostic],
    canonical_text: str,
    has_error: bool,
) -> dict[str, int]:
    front_matter = typed_list(book.get("front_matter"))
    chapters = typed_list(book.get("chapters"))
    back_matter = typed_list(book.get("back_matter"))
    footnotes = typed_list(book.get("footnotes"))

    paragraph_count = 0
    total_text_chars = 0
    removed_section_count = 0

    # v3.0: paragraph_count counts only public EpubParagraph objects, which
    # live exclusively in front/back matter sections. Chapter paragraphs are
    # internal and exposed only via chapter.text.
    for section in [*front_matter, *back_matter]:
        paragraph_count += len(typed_list(section.get("paragraphs")))

    for container in [*front_matter, *chapters, *back_matter]:
        text = str(container.get("text", ""))
        total_text_chars += len(text)
        if "included_in_canonical_text" in container and not bool(container.get("included_in_canonical_text")):
            removed_section_count += 1

    warning_count = sum(1 for item in diagnostics if item.severity == "warning")
    error_count = sum(1 for item in diagnostics if item.severity == "error")
    if has_error:
        error_count = max(error_count, 1)

    return {
        "chapter_count": len(chapters),
        "front_matter_section_count": len(front_matter),
        "back_matter_section_count": len(back_matter),
        "paragraph_count": paragraph_count,
        "footnote_count": len(footnotes),
        "total_text_chars": total_text_chars,
        "canonical_text_chars": len(canonical_text),
        "removed_section_count": removed_section_count,
        "warning_count": warning_count,
        "error_count": error_count,
    }


def validate_result(
    result: dict[str, object],
    max_output_json_bytes: int,
    *,
    allow_internal: bool = False,
) -> None:
    payload = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > max_output_json_bytes:
        if allow_internal:
            return
        raise DomainFailure("internal_error", "Serialized result exceeded output limit.")
    validator = Draft202012Validator(result_schema())
    errors = sorted(validator.iter_errors(result), key=lambda item: list(item.path))
    if errors:
        raise DomainFailure("internal_error", f"Structured result failed schema validation: {errors[0].message}")


def first_dc_value(book: epub.EpubBook, key: str) -> str | None:
    values = dc_values(book, key)
    return values[0] if values else None


def dc_values(book: epub.EpubBook, key: str) -> list[str]:
    return [normalize_text(str(value)) for value, _attrs in book.get_metadata("DC", key)]


def first_meta_value(book: epub.EpubBook, key: str) -> str | None:
    for namespace, name in [("OPF", "meta"), ("DC", key)]:
        for value, attrs in book.get_metadata(namespace, name):
            if attrs.get("property") == key or attrs.get("name") == key:
                return normalize_text(str(value))
    opf_namespace = "http://www.idpf.org/2007/opf"
    opf_meta = getattr(book, "metadata", {}).get(opf_namespace, {})
    if key in opf_meta and opf_meta[key]:
        value, _attrs = opf_meta[key][0]
        if value is not None:
            return normalize_text(str(value))
    if key == "dcterms:modified" and None in opf_meta:
        for value, attrs in opf_meta[None]:
            if attrs.get("property") == "dcterms:modified" and value is not None:
                return normalize_text(str(value))
    return None


def normalize_metadata_date(
    value: str | None,
    diagnostics: list[Diagnostic],
) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        return normalized
    try:
        dt = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        diagnostics.append(diagnostic("metadata_date_invalid", entity_type="book", field="metadata"))
        return None
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_english_like_language(value: str) -> bool:
    normalized = value.strip().strip("\"'").replace("_", "-").lower()
    return normalized in {"en", "eng", "english"} or normalized.startswith("en-")


def container_text(container: dict[str, object], *, include_title: bool) -> str:
    text = str(container.get("text", "")).strip()
    title = str(container.get("title", "")).strip()
    if include_title and title:
        return f"{title}\n\n{text}".strip()
    return text


def diagnostic(
    code: str,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    field: str | None = None,
    message: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=DIAGNOSTIC_SEVERITY_BY_CODE[code],
        message=message or DEFAULT_DIAGNOSTIC_MESSAGES[code],
        entity_type=entity_type,
        entity_id=entity_id,
        field=field,
    )


def sort_diagnostics(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    rank = {
        "html_document_parse_timeout_skipped": -1,
        "html_document_too_large_skipped": -1,
        "front_matter_detected": 0,
        "chapter_title_detected": 1,
        "footnote_detected": 2,
        "footnote_marker_removed": 3,
        "back_matter_detected": 4,
        "empty_readable_content": 99,
    }
    return sorted(
        diagnostics,
        key=lambda item: (
            rank.get(item.code, 100),
            item.entity_id or "",
            item.field or "",
            item.code,
        ),
    )


def typed_list(value: object) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [typed_dict(item) for item in value]
    return []


def typed_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def dedupe_consecutive(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if not result or result[-1] != item:
            result.append(item)
    return result


def normalize_href(href: str) -> str:
    return href.split("#", 1)[0]


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def duration_ms(started: datetime) -> int:
    return max(0, int((datetime.now(tz=UTC) - started).total_seconds() * 1000))


def set_fault_injection(
    *,
    pipeline_timeout: bool = False,
    html_parse_timeout_hrefs: frozenset[str] | None = None,
    source_file_overrides: dict[str, dict[str, object]] | None = None,
) -> None:
    global _FAULT_INJECTION
    _FAULT_INJECTION = FaultInjection(
        pipeline_timeout=pipeline_timeout,
        html_parse_timeout_hrefs=html_parse_timeout_hrefs or frozenset(),
        source_file_overrides=source_file_overrides,
    )


def reset_fault_injection() -> None:
    set_fault_injection()
