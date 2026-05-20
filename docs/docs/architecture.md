# Architecture

`epub_content_extractor` is a standalone Python module and CLI-oriented transform component. It converts a local EPUB file into a structured extraction result that is safe for downstream English NLP pipelines.

## Pipeline

1. Validate configuration against `docs/schemas/epub_content_extractor_config.v3.0.schema.json`.
2. Validate local input path and file constraints.
3. Apply archive safety checks before OPF/package discovery.
4. Discover EPUB container and OPF package.
5. Read manifest, spine, metadata, NAV/TOC where available.
6. Extract readable XHTML blocks in spine order.
7. Classify front matter, chapters, back matter, notes, and structural assets.
8. Normalize text, ids, metadata, diagnostics, and summary counts.
9. Return a schema-valid result.

## Language contract

The module is English-only for product-level downstream use. It does not run language detection by default. Output `book.language` is always `en`.

## Determinism

For identical input bytes, config, extractor version, and dependency versions, the normalized output must be deterministic except for documented volatile timestamps or duration fields.
