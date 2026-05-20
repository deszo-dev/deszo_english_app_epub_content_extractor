# Input / Output Contract

## Input

`extract_epub_content` accepts a local readable file path. The `.epub` extension is advisory. EPUB validity is determined by ZIP/container/package/security checks, not by filename alone.

## Top-level result

The canonical result schema is `docs/schemas/epub_content_extractor.v3.0.schema.json`.

Required top-level fields:

- `schema_version` — exactly `epub_content_extractor.v3.0`;
- `status` — `succeeded` or `failed`;
- `diagnostics` — production-safe diagnostics array;
- `extraction` — extractor version, timing, effective config snapshot, and summary.

On success, `book` is required, `error` is absent, readable content must exist, and `book.language` is `en`.

On failure, `error` is required and `book` is absent.

## Structured failure model

Expected domain failures must be structured result failures, not exceptions, when a result can be built.

## Canonical text

Canonical text is derived by `build_canonical_text(book, options=None)`. It is not stored as a primary field on `EpubBook`.


## No readable content policy

If an EPUB package is structurally readable but produces no non-empty readable text blocks after spine, manifest, media-type, and HTML parsing filters, extraction MUST fail with a structured `no_readable_content` error. A `succeeded` result MUST NOT be emitted without at least one readable chapter or section text block unless a future schema version explicitly introduces a structural-only success mode.
