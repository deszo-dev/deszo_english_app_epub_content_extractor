# EPUB Content Extractor

`epub_content_extractor` extracts structured book content from local `.epub` files and returns a JSON-serializable result that follows the `epub_content_extractor.v3.0` contract.

The module is designed for downstream English-language NLP pipelines. It does not expose HTTP APIs, databases, queues, or storage integrations. The public surfaces are:

- a Python library API;
- a CLI command.

## Current Contract

The primary output is a structured result object, not plain text.

Successful results contain:

- `book.title`, `book.subtitle`, `book.language`;
- authors and contributors;
- normalized EPUB metadata;
- front matter, chapters, back matter;
- footnotes;
- table of contents;
- lightweight asset metadata;
- diagnostics;
- extraction metadata and summary.

Failed results contain:

- `status = "failed"`;
- a structured `error`;
- `diagnostics`;
- `extraction` metadata with config snapshot and summary.

The canonical schema lives in:

- [docs/architecture/schema/epub_content_extractor.v3.0.schema.json](C:/my/2026/deszo_english_app/deszo_english_app_epub_content_extractor/docs/architecture/schema/epub_content_extractor.v3.0.schema.json)
- [docs/architecture/schema/epub_content_extractor_config.v3.0.schema.json](C:/my/2026/deszo_english_app/deszo_english_app_epub_content_extractor/docs/architecture/schema/epub_content_extractor_config.v3.0.schema.json)

The detailed contract and testing docs live in:

- [docs/architecture/epub_content_extractor_architecture.md](C:/my/2026/deszo_english_app/deszo_english_app_epub_content_extractor/docs/architecture/epub_content_extractor_architecture.md)
- [docs/testing/epub_content_extractor_testing.md](C:/my/2026/deszo_english_app/deszo_english_app_epub_content_extractor/docs/testing/epub_content_extractor_testing.md)

## Python API

```python
from epub_content_extractor import (
    EpubCanonicalTextBuildOptions,
    EpubContentExtractorConfig,
    build_canonical_text,
    extract_epub_content,
)

result = extract_epub_content(
    "book.epub",
    config=EpubContentExtractorConfig(),
)

if result["status"] == "succeeded":
    book = result["book"]
    text = build_canonical_text(
        book,
        options=EpubCanonicalTextBuildOptions(include_front_matter=True),
    )
else:
    print(result["error"]["code"])
```

In v3.0 chapters expose only `chapter.text` as their public body — there is no `chapters[].paragraphs` array. Public `EpubParagraph` objects live only inside front/back-matter sections.

Public exports include:

- `extract_epub_content(input_path, config=None) -> dict`;
- `build_canonical_text(book, options=None) -> str`;
- `EpubCanonicalTextBuildOptions(include_front_matter=False, include_back_matter=False, include_footnotes=False, include_chapter_titles=True, include_section_titles=False)`;
- `EpubContentExtractorConfig`;
- `EpubContentExtractorPipeline.runtime_metadata()`.

Compatibility helpers are also still exported:

- `extract_document(...)`;
- `extract_text_from_epub(...)`.

`extract_text_from_epub()` is now a convenience wrapper around the structured API and canonical text builder.

## CLI

Extract to stdout:

```bash
epub-content-extractor extract book.epub
```

Write JSON to a file:

```bash
epub-content-extractor extract book.epub --output result.json --pretty
```

Read config from a file:

```bash
epub-content-extractor extract book.epub --config config.json
```

Read config from stdin:

```bash
type config.json | epub-content-extractor extract book.epub --config -
```

Enable top-level debug payload:

```bash
epub-content-extractor extract book.epub --include-debug
```

CLI rules:

- stdout is reserved for machine-readable JSON output;
- `--version` prints only the version;
- `--output -` means stdout;
- `--config -` reads config JSON from stdin;
- output file writes use atomic replace in the target directory.

Exit codes:

- `0`: success
- `1`: expected extraction/input failure
- `3`: output write failure
- `4`: invalid config
- `99`: internal error

## Config

The config contract is closed: unknown fields are invalid, except for tooling-only `$schema`.

Current fields include:

- `include_front_matter_in_canonical_text`
- `include_back_matter_in_canonical_text`
- `include_footnotes_in_canonical_text`
- `include_chapter_titles_in_canonical_text`
- `include_section_titles_in_canonical_text`
- `max_epub_size_bytes`
- `max_html_document_size_bytes`
- `max_text_block_chars`
- `pipeline_timeout_seconds`
- `html_parse_timeout_seconds`
- `max_archive_uncompressed_bytes`
- `max_archive_entry_count`
- `max_archive_compression_ratio`
- `max_toc_depth`
- `max_diagnostic_count`
- `max_output_json_bytes`
- `include_debug`

The default config snapshot is exposed by `default_config_dict()`.

## Runtime Metadata

The package exposes deterministic runtime metadata for staged orchestration:

```python
from epub_content_extractor import EpubContentExtractorPipeline

metadata = EpubContentExtractorPipeline().runtime_metadata()
```

This includes stage metadata, source fingerprints, dependency information, and stage fingerprint helpers for reuse/invalidation logic.

## Testing Status

The project currently includes:

- schema validation tests;
- registry drift tests;
- golden snapshot tests for all documented fixtures in `docs/testing`;
- fault-injection tests for timeout paths;
- public API and CLI tests.

Current local test command:

```bash
pytest -q
```

At the moment the suite passes with:

```text
14 passed
```

## Implementation Notes

The current implementation already covers the main v3.0 contract, including:

- structured success/failure results;
- archive safety validation;
- spine-ordered extraction;
- front matter / chapter / back matter separation;
- footnote extraction and marker removal;
- canonical text construction;
- deterministic diagnostics ordering.

Some behavior is still heuristic by nature, especially around structural inference from publisher-specific EPUB markup. For exact expected behavior, treat the schema artifacts and documented golden fixtures as the source of truth.

## License

The package metadata currently declares non-commercial use. See [LICENSE](C:/my/2026/deszo_english_app/deszo_english_app_epub_content_extractor/LICENSE).
