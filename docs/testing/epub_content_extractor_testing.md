# Testing Guide for `epub_content_extractor`

## 1. Scope

This guide covers automated testing for `epub_content_extractor` contract version `v2.2`.

The module under test converts local `.epub` files into a JSON-serializable structured result object with:

* `schema_version = "epub_content_extractor.v2.2"`;
* `status = "succeeded"` or `"failed"`;
* structured `book` output on success;
* structured `error` output on failure;
* production `diagnostics`;
* `extraction` metadata and summary;
* optional `debug` data only when enabled.

Tested interfaces:

* Python library entry point:

```python
extract_epub_content(input_path: str | Path, config: dict | None = None) -> dict
```

* Python canonical text builder:

```python
build_canonical_text(book: dict, options: dict | None = None) -> str
```

* CLI command:

```bash
epub-content-extractor extract INPUT.epub [options]
```

Tested behavior:

* valid EPUB extraction;
* dynamically generated EPUB fixtures;
* config validation;
* input file validation;
* EPUB ZIP/archive validation;
* EPUB manifest/OPF handling;
* language contract;
* metadata normalization;
* chapter/section/paragraph extraction invariants;
* footnote extraction invariants;
* TOC handling;
* asset metadata handling;
* output schema validation;
* diagnostic code/severity compliance;
* error code and CLI exit-code mapping;
* deterministic behavior;
* debug-mode behavior;
* filesystem/path safety;
* resource limits;
* regression cases for silent success, unstable ordering, schema/docs drift, and fatal-error precedence.

Not tested as module-owned behavior:

* HTTP API behavior;
* authentication/authorization;
* database persistence;
* queue processing;
* remote object storage;
* OCR;
* visual EPUB rendering;
* CSS/page layout preservation;
* binary image extraction;
* non-English language detection;
* downstream NLP sentence segmentation.

Important testing requirement:

All EPUB inputs in automated tests must be generated dynamically inside the test temporary directory. Tests must not depend on committed binary EPUB fixtures. Valid EPUB files should be generated with a ready EPUB library, preferably Python `ebooklib`. Invalid/archive-security EPUBs should be generated with ZIP utilities such as Python `zipfile`, because EPUB libraries may sanitize unsafe paths and prevent malformed cases from being created.

Canonical fixture policy:

- Contract tests MUST NOT commit generated binary EPUB files as source fixtures.
- Each contract fixture MUST be represented by committed deterministic fixture source artifacts.
- The test helper generates `input.epub` or an invalid ZIP/EPUB-like file under the test temporary directory at runtime.
- Valid EPUB files SHOULD be generated with `ebooklib` or an equivalent pinned helper.
- Invalid/archive-security inputs SHOULD be generated with Python `zipfile` or an external fixture tool when `zipfile` cannot create the required invalid condition.
- Key contract fixtures SHOULD include normalized golden outputs once implementation behavior is accepted.

Required source layout for each contract fixture:

```text
tests/fixtures/epub_content_extractor/<category>/<fixture_id>/fixture.json
tests/fixtures/epub_content_extractor/<category>/<fixture_id>/config.json
tests/fixtures/epub_content_extractor/<category>/<fixture_id>/expected.normalized.json
```

`expected.normalized.json` is omitted only when the test is explicitly invariant-only, schema-only, fault-injection-only, or a documented open contract decision.

---

## 2. Assumptions and Documentation Gaps

| Area                                  | Issue                                                                                                                             | Risk                                                                                               | Required clarification                                                                                                                                          |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EPUB fixture generation               | Documentation requires EPUB inputs but does not prescribe a canonical test-generation library.                                    | Different generators may produce slightly different OPF/NCX/NAV files, causing brittle assertions. | Standardize on `ebooklib` for valid EPUBs and `zipfile` for intentionally invalid/security EPUBs.                                                               |
| Exact chapter detection heuristics    | Chapter detection may use TOC, spine order, headings, or internal scoring.                                                        | Exact chapter boundaries may vary while still satisfying contract.                                 | Tests should assert stable contract invariants, not internal scoring decisions, unless fixture is intentionally simple.                                         |
| Front/back matter classification      | Section detection is heuristic.                                                                                                   | Tests may become brittle if exact classification changes while output remains contract-valid.      | Use strong explicit titles such as `Copyright`, `Preface`, `Appendix`, `Advertisement` and assert type only when docs define expected behavior strongly enough. |
| `chapter_title_uncertain`             | The code exists in the v2.2 schema but is `reserved_not_emitted_by_default` in the diagnostic registry.                            | Production tests must not require a triggering EPUB in v2.2.                                       | Assert that default production fixtures do not emit this code; add a deterministic trigger only in a future version if the registry status changes.              |
| `chapter_type_uncertain`              | The code exists in the v2.2 schema but is `reserved_not_emitted_by_default` in the diagnostic registry.                            | Production tests must not require a triggering EPUB in v2.2.                                       | Assert that default production fixtures do not emit this code; add a deterministic trigger only in a future version if the registry status changes.              |
| `toc_target_unresolved`               | Contract says unresolved TOC target should emit diagnostic, but exact unresolved-target detection depends on TOC parser behavior. | Different libraries may normalize/remove broken TOC items before extractor sees them.              | Use a hand-crafted EPUB ZIP with explicit NCX/NAV broken target if strict coverage is required.                                                                 |
| `html_document_parse_timeout_skipped` | Timeout is timing-dependent.                                                                                                      | Flaky tests if relying on real wall-clock parser timeout.                                          | Implement as integration/fault-injection test using parser fake/hook, or mark as non-deterministic without test seam.                                           |
| `pipeline_timeout`                    | Whole-pipeline timeout is timing-dependent.                                                                                       | Flaky test if based on slow machine behavior.                                                      | Needs deterministic clock/timer injection or a test-only timeout hook.                                                                                          |
| `unicode_normalization_failed`        | Documentation does not define deterministic invalid Unicode input that must partially fail.                                       | Hard to trigger reliably with Python strings and EPUB XML.                                         | Cover schema/severity mapping; add deterministic fixture only after implementation exposes known failure condition.                                             |
| `text_block_too_large_dropped`        | Docs define split-or-drop policy but not exact condition where splitting is unsafe.                                               | Test may expect drop while implementation safely splits.                                           | Use invariant-based split test; require clarification for forced drop fixture.                                                                                  |
| `output_json_too_large`               | Docs say exceeding `max_output_json_bytes` maps to `internal_error` in v2.2 because no dedicated code exists.                     | Semantically odd regression target.                                                                | Test only CLI/library behavior documented for v2.2; recommend future dedicated error code.                                                                      |
| Manifest generation                   | The module parses EPUB package/OPF manifest but does not define a separate output manifest artifact.                              | Generic tests for “manifest generation” would be invalid.                                          | Do not test external manifest files; test `book.assets`, TOC, source metadata, and schema-valid output instead.                                                 |
| Logs                                  | Documentation gives privacy rules for logs but no stable logging API.                                                             | Direct log assertions may be brittle.                                                              | Treat as optional observability tests unless implementation exposes logger contract.                                                                            |
| Permission errors                     | File permission behavior is OS-dependent, especially on Windows.                                                                  | Cross-platform test instability.                                                                   | Run permission test only on POSIX-capable CI or use monkeypatch/fake filesystem.                                                                                |

---

## 3. Test Strategy

### 3.1 Unit tests

Unit tests should cover pure or near-pure contract behavior:

* config schema validation;
* default config snapshot shape;
* canonical text builder behavior;
* invalid builder inputs;
* diagnostic code/severity registry consistency;
* result schema validation against synthetic result examples;
* summary-count invariants.

Pass condition:

* the tested function returns or raises exactly according to contract;
* no EPUB parsing is required unless the unit is specifically EPUB generation.

Required fixtures:

* minimal valid `book` dictionary for `build_canonical_text`;
* official result schema;
* official config schema;
* diagnostic severity matrix.

### 3.2 Integration tests

Integration tests should call the public library and CLI against generated EPUB files.

They should verify:

* success/failure status;
* result validates against official result schema;
* expected error code or diagnostics;
* schema version;
* config snapshot;
* extracted content invariants;
* no forbidden fields or paths;
* CLI exit code and output channel behavior.

Required fixtures:

* dynamically generated valid EPUBs via `ebooklib`;
* hand-crafted invalid ZIP/EPUB files via `zipfile`;
* temp directories for input/output isolation.

### 3.3 Contract tests

Contract tests should enforce stable public behavior:

* top-level success/failure object shape;
* `book` and `error` mutual exclusivity;
* `schema_version`;
* fixed output language `"en"`;
* error code matrix;
* diagnostic code/severity matrix;
* CLI exit code mapping;
* debug absent/present policy.

Pass condition:

* every production result validates against `schema/epub_content_extractor.v2.2.schema.json`;
* every emitted diagnostic code is documented;
* every emitted diagnostic severity matches the matrix;
* every failure has exactly one top-level `error`.

### 3.4 Schema validation tests

Schema validation tests should validate:

* valid minimal success result;
* valid failed result;
* invalid success result with no readable content;
* invalid success result containing `severity = "error"` diagnostic;
* invalid debug field when `include_debug = false`;
* config schema unknown fields;
* config schema wrong types;
* config hard maximums.

Pass condition:

* official schemas accept valid objects and reject invalid objects.

### 3.5 Golden/invariant tests

Because timestamps and duration are allowed to differ, golden tests must normalize volatile fields before comparison through a named helper contract:

```python
def normalize_result_for_snapshot(result: dict) -> dict:
    ...
```

The helper may replace only these fields:

* `extraction.started_at` with `"1970-01-01T00:00:00Z"`;
* `extraction.finished_at` with `"1970-01-01T00:00:00Z"`;
* `extraction.duration_ms` with `0`.

The helper MUST be schema-preserving: the normalized result and each committed `expected.normalized.json` MUST still validate against `schema/epub_content_extractor.v2.2.schema.json`.

The helper MUST NOT sort arrays, rewrite IDs, normalize diagnostics order, normalize file hashes, normalize file sizes, or hide dependency/version differences. A test MUST fail if an unknown volatile field appears.

Golden comparisons should focus on:

* normalized content;
* IDs;
* ordering;
* diagnostics codes/severities;
* summary counts;
* metadata normalization.

### 3.6 Negative and security tests

Negative tests must cover:

* missing file;
* directory input;
* plain text with `.epub` extension;
* valid ZIP that is not an EPUB;
* missing/unreadable OPF;
* archive path traversal;
* absolute archive paths;
* excessive archive entry count;
* excessive archive compression ratio;
* excessive EPUB file size;
* invalid config precedence over input validation.

Pass condition:

* expected `error.code`;
* expected CLI exit code;
* structured JSON exists when contract says it should;
* no partial `book` on failure;
* no unexpected files created.

### 3.7 Property/invariant-based tests

Property-style tests should cover:

* generated valid EPUBs always return schema-valid result or documented failure;
* no emitted diagnostic uses undocumented code;
* warning/error summary counts match diagnostics;
* no absolute local paths appear in production output;
* `chapter.text` equals paragraph texts joined with `"\n\n"`;
* repeated runs produce semantically equal output after volatile fields are normalized.


### 3.8 Deterministic fault-injection tests

Timeout and unexpected-failure paths MUST NOT be tested by relying on wall-clock sleeps or machine slowness.

The implementation SHOULD expose an internal test-only dependency injection seam, not part of the stable public API, for:

- forcing one selected HTML document parse operation to raise or return a parse-timeout signal;
- forcing the whole-pipeline deadline check to fail before extraction completes;
- forcing JSON serialization size-check overflow;
- forcing output atomic replace failure in CLI tests.

The seam MUST be unavailable or unused in normal production calls. It MUST NOT alter the public result schema, config schema, CLI flags, or production semantics.

Tests using this seam MUST assert the same public output that a real timeout or failure would produce.

---

## 4. Test Fixtures

Contract tests use committed fixture generator specs and normalized expected outputs. Binary EPUB/ZIP inputs are generated at test runtime under a temporary directory.

Required fixture files for new contract fixtures:

```text
fixture.json
config.json
expected.normalized.json
```

`fixture.json` describes how to generate the EPUB or ZIP input and SHOULD validate against `schema/epub_content_extractor_fixture_manifest.v2.2.schema.json`. The test helper generates `input.epub` under the test temporary directory at runtime.

`expected.normalized.json` is compared after applying `normalize_result_for_snapshot()`. The normalizer may replace only `extraction.started_at`, `extraction.finished_at`, and `extraction.duration_ms`.

A test MUST fail if output contains an additional volatile field that is not listed above.



### 4.1 Golden-output acceptance artifacts

The documentation package defines the required locations and comparison rules for golden outputs, but generated `expected.normalized.json` files MUST be populated from either:

1. manually approved contract examples, or
2. a run of the accepted implementation followed by contract review.

Do not commit placeholder JSON under the name `expected.normalized.json`. A file with that name is normative and MUST be valid against the result schema after the documented normalization policy is applied.

Minimum required golden outputs for 9+/10 readiness:

```text
tests/fixtures/epub_content_extractor/success/minimal_valid/expected.normalized.json
tests/fixtures/epub_content_extractor/success/complex_valid/expected.normalized.json
tests/fixtures/epub_content_extractor/failure/plain_text_epub_extension/expected.normalized.json
tests/fixtures/epub_content_extractor/failure/valid_zip_not_epub/expected.normalized.json
tests/fixtures/epub_content_extractor/security/path_traversal/expected.normalized.json
tests/fixtures/epub_content_extractor/config/unknown_field/expected.normalized.json
tests/fixtures/epub_content_extractor/limits/no_readable_content/expected.normalized.json
```

Until those files exist, fixture tests MUST be treated as acceptance TODOs rather than completed golden-snapshot tests.

The minimum golden-output acceptance manifest is stored at:

```text
docs/testing/epub_content_extractor_golden_acceptance_manifest.v2.2.json
```

It MUST validate against:

```text
schema/epub_content_extractor_golden_acceptance_manifest.v2.2.schema.json
```

Release validation MUST fail when the manifest status is `pending_until_real_goldens_committed`. Release validation may pass only when `status = "complete"` and every listed `expected.normalized.json` path exists, is non-placeholder JSON, and validates against the result schema after the documented schema-preserving snapshot-normalization policy.


### Fixture F000: Default effective config

**Purpose:**
Reusable default config snapshot expected after missing config or `{}` input.

**Config:**

```json
{
  "include_front_matter_in_canonical_text": false,
  "include_back_matter_in_canonical_text": false,
  "include_footnotes_in_canonical_text": false,
  "include_chapter_titles_in_canonical_text": true,
  "include_section_titles_in_canonical_text": false,
  "max_epub_size_bytes": 104857600,
  "max_html_document_size_bytes": 10485760,
  "max_text_block_chars": 100000,
  "pipeline_timeout_seconds": 120,
  "html_parse_timeout_seconds": 20,
  "max_archive_uncompressed_bytes": 524288000,
  "max_archive_entry_count": 10000,
  "max_archive_compression_ratio": 100,
  "max_toc_depth": 8,
  "max_diagnostic_count": 1000,
  "max_output_json_bytes": 524288000,
  "include_debug": false
}
```

**Expected reusable assertions:**

* `result.extraction.config` equals this object when no custom config is supplied.
* `"$schema"` is never present in `result.extraction.config`.
* All numeric values are integers.
* `include_debug` is `false`.

---

### Fixture F001: Minimal valid EPUB generated with `ebooklib`

**Purpose:**
Smallest stable happy-path EPUB with one readable chapter, metadata, language, author, and TOC.

**Generation rule:**
Generate dynamically in a test temp directory using `ebooklib`. Do not store binary EPUB in repository.

**Output file:**

`tmp/epubs/minimal_valid.epub`

**Encoding:**
UTF-8 for all XHTML/metadata strings.

**EPUB metadata:**

```json
{
  "identifier": {
    "scheme": "Project Gutenberg",
    "value": "TEST-001"
  },
  "title": "Minimal Test Book",
  "language": "en",
  "authors": [
    "Jane Example"
  ],
  "publisher": "Test Publisher",
  "rights": "Public domain",
  "subjects": [
    "Testing"
  ],
  "published_at": "2026-05-08"
}
```

**Spine / reading order:**

```json
[
  "nav",
  "chapter_1.xhtml"
]
```

**TOC:**

```json
[
  {
    "title": "Chapter One",
    "href": "chapter_1.xhtml"
  }
]
```

**File / content object:**

`OEBPS/chapter_1.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Chapter One</title>
  </head>
  <body>
    <h1>Chapter One</h1>
    <p>First paragraph of the minimal generated EPUB.</p>
    <p>Second paragraph with clean English text.</p>
  </body>
</html>
```

**Config:**
Use missing config or `{}`.

**Expected reusable assertions:**

* library result has `status = "succeeded"`;
* result validates against `schema/epub_content_extractor.v2.2.schema.json`;
* `schema_version = "epub_content_extractor.v2.2"`;
* `book.language = "en"`;
* `book.title = "Minimal Test Book"`;
* `book.authors` contains exactly one author named `"Jane Example"` with role `"author"`;
* `book.chapters.length >= 1`;
* first chapter has non-empty `text`;
* first chapter has at least two paragraphs;
* `chapter.text` does not include `"Chapter One"` if `chapter.title = "Chapter One"`;
* `chapter.text` equals `paragraphs[].text` joined with `"\n\n"`;
* `book.error` is absent;
* no diagnostic has `severity = "error"`;
* `metadata.source_file.sha256` matches lowercase 64-char hex pattern;
* `metadata.source_file.size_bytes` equals actual EPUB file size;
* `metadata.source_file.file_name`, if emitted, is basename only and contains no slash or backslash.

---

### Fixture F002: Complex EPUB with front matter, chapters, back matter, footnote, TOC, and image asset

**Purpose:**
Valid richer EPUB for integration coverage.

**Generation rule:**
Generate dynamically with `ebooklib`.

**Output file:**

`tmp/epubs/complex_valid.epub`

**EPUB metadata:**

```json
{
  "identifier": {
    "scheme": "Project Gutenberg",
    "value": "TEST-002"
  },
  "title": "Complex Test Book",
  "subtitle": "Fixture Edition",
  "language": "en-US",
  "authors": [
    "Alice Writer",
    "Bob Writer"
  ],
  "contributors": [
    {
      "name": "Clara Translator",
      "role": "translator"
    }
  ],
  "publisher": "Test Publisher",
  "rights": "Public domain",
  "subjects": [
    "Testing",
    "Drama"
  ],
  "published_at": "2026-05-08",
  "modified_at": "2026-05-08T10:00:00Z"
}
```

**Spine / reading order:**

```json
[
  "nav",
  "front_preface.xhtml",
  "chapter_1.xhtml",
  "chapter_2.xhtml",
  "back_appendix.xhtml"
]
```

**TOC:**

```json
[
  {
    "title": "Preface",
    "href": "front_preface.xhtml"
  },
  {
    "title": "Chapter One",
    "href": "chapter_1.xhtml"
  },
  {
    "title": "Chapter Two",
    "href": "chapter_2.xhtml"
  },
  {
    "title": "Appendix",
    "href": "back_appendix.xhtml"
  }
]
```

**Files / content objects:**

`OEBPS/front_preface.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Preface</title>
  </head>
  <body>
    <h1>Preface</h1>
    <p>This preface explains why the generated book exists.</p>
  </body>
</html>
```

`OEBPS/chapter_1.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Chapter One</title>
  </head>
  <body>
    <h1>Chapter One</h1>
    <p>The first chapter has a linked note<a href="notes.xhtml#fn1"><sup>1</sup></a>.</p>
    <p>The second paragraph remains ordinary text.</p>
    <aside id="fn1">
      <p><sup>1</sup> This is the generated footnote text.</p>
    </aside>
    <img src="images/cover.png" alt="Generated cover image" />
  </body>
</html>
```

`OEBPS/chapter_2.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Chapter Two</title>
  </head>
  <body>
    <h1>Chapter Two</h1>
    <p>The second chapter confirms reading order.</p>
  </body>
</html>
```

`OEBPS/back_appendix.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Appendix</title>
  </head>
  <body>
    <h1>Appendix</h1>
    <p>This appendix is generated back matter.</p>
  </body>
</html>
```

`OEBPS/images/cover.png`

```text
Use a valid 1x1 PNG binary generated dynamically by the test helper. The binary must not be asserted in output; only metadata may be asserted.
```

**Config:**

```json
{
  "include_front_matter_in_canonical_text": true,
  "include_back_matter_in_canonical_text": true,
  "include_footnotes_in_canonical_text": false,
  "include_chapter_titles_in_canonical_text": true,
  "include_section_titles_in_canonical_text": true,
  "max_epub_size_bytes": 104857600,
  "max_html_document_size_bytes": 10485760,
  "max_text_block_chars": 100000,
  "pipeline_timeout_seconds": 120,
  "html_parse_timeout_seconds": 20,
  "max_archive_uncompressed_bytes": 524288000,
  "max_archive_entry_count": 10000,
  "max_archive_compression_ratio": 100,
  "max_toc_depth": 8,
  "max_diagnostic_count": 1000,
  "max_output_json_bytes": 524288000,
  "include_debug": false
}
```

**Expected reusable assertions:**

* result succeeds and validates against schema;
* output contains no binary image data or base64 image content;
* `book.assets` may contain image metadata with `media_type` and optional basename file name;
* `book.table_of_contents[].children` is always an array;
* chapter numbers are 1-based and in reading order;
* `summary.chapter_count` equals `book.chapters.length`;
* `summary.paragraph_count` equals total paragraphs in front matter, chapters, and back matter;
* `summary.warning_count` equals diagnostics with `severity = "warning"`;
* `summary.error_count = 0`.

---

### Fixture F003: Valid EPUB with missing metadata

**Purpose:**
Verify missing title, author, language, TOC behavior is non-fatal and diagnostic-driven.

**Generation rule:**
Generate dynamically with `ebooklib`, but omit title, author, language, and TOC if library permits. If the library requires title or language, generate with `zipfile` using a valid EPUB structure and OPF that omits `dc:title`, `dc:creator`, and `dc:language`.

**Output file:**

`tmp/epubs/missing_metadata.epub`

**Required EPUB internal files when hand-crafted:**

`mimetype`

```text
application/epub+zip
```

`META-INF/container.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
```

`OEBPS/content.opf`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">TEST-003</dc:identifier>
  </metadata>
  <manifest>
    <item id="chap1" href="chapter_1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
  </spine>
</package>
```

`OEBPS/chapter_1.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title></title>
  </head>
  <body>
    <p>This generated EPUB intentionally has no title, author, language, or TOC metadata.</p>
  </body>
</html>
```

**Config:**
Use fixture F000.

**Expected reusable assertions:**

* extraction succeeds;
* `book.language = "en"`;
* `book.title = null`;
* `book.authors = []`;
* diagnostics contain:

  * `metadata_missing_title` with severity `warning`;
  * `metadata_missing_author` with severity `info`;
  * `metadata_language_missing` with severity `info`;
* diagnostics may contain `table_of_contents_missing` with severity `info`;
* no diagnostic has `severity = "error"`;
* result validates against schema.

---

### Fixture F004: EPUB with non-English metadata language but English content

**Purpose:**
Verify fixed English output contract and metadata-language conflict warning.

**Generation rule:**
Generate dynamically with `ebooklib`.

**Output file:**

`tmp/epubs/non_english_metadata_language.epub`

**EPUB metadata:**

```json
{
  "identifier": {
    "scheme": "Test",
    "value": "TEST-004"
  },
  "title": "Language Conflict Book",
  "language": "fr",
  "authors": [
    "Jane Example"
  ]
}
```

**Content:**

`OEBPS/chapter_1.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Chapter One</title>
  </head>
  <body>
    <h1>Chapter One</h1>
    <p>This content is English, but metadata declares French.</p>
  </body>
</html>
```

**Config:**
Use fixture F000.

**Expected reusable assertions:**

* extraction succeeds;
* `book.language = "en"`;
* diagnostics contain `metadata_language_conflicts_with_contract` with severity `warning`;
* warning count equals number of warning diagnostics;
* result validates against schema.

---

### Fixture F005: EPUB with invalid date metadata

**Purpose:**
Verify invalid date normalization behavior.

**Generation rule:**
Generate dynamically with `ebooklib` or hand-crafted OPF.

**Output file:**

`tmp/epubs/invalid_date.epub`

**EPUB metadata:**

```json
{
  "identifier": {
    "scheme": "Test",
    "value": "TEST-005"
  },
  "title": "Invalid Date Book",
  "language": "en",
  "authors": [
    "Date Tester"
  ],
  "published_at": "not-a-date"
}
```

**Content:**

`OEBPS/chapter_1.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Chapter One</title>
  </head>
  <body>
    <h1>Chapter One</h1>
    <p>This book contains invalid publication date metadata.</p>
  </body>
</html>
```

**Config:**
Use fixture F000.

**Expected reusable assertions:**

* extraction succeeds;
* `book.metadata.published_at = null`;
* diagnostics contain `metadata_date_invalid` with severity `warning`;
* production output does not contain raw string `"not-a-date"` outside optional redacted debug data;
* result validates against schema.

---

### Fixture F006: EPUB with duplicate metadata values

**Purpose:**
Verify deduplication of identifiers, subjects, authors, and contributors.

**Generation rule:**
Generate dynamically with `ebooklib`; if duplicate metadata cannot be represented through the high-level API, hand-craft OPF.

**Output file:**

`tmp/epubs/duplicate_metadata.epub`

**OPF metadata intent:**

```json
{
  "identifiers": [
    {
      "scheme": "Test",
      "value": "DUP-001"
    },
    {
      "scheme": "Test",
      "value": "DUP-001"
    }
  ],
  "title": "Duplicate Metadata Book",
  "language": "en",
  "authors": [
    "Repeat Author",
    "Repeat Author"
  ],
  "subjects": [
    "Drama",
    " drama ",
    "Testing"
  ]
}
```

**Content:**

`OEBPS/chapter_1.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Chapter One</title>
  </head>
  <body>
    <h1>Chapter One</h1>
    <p>This book is used to verify metadata deduplication.</p>
  </body>
</html>
```

**Config:**
Use fixture F000.

**Expected reusable assertions:**

* extraction succeeds;
* identifiers are deduplicated by normalized scheme/value;
* authors are deduplicated by normalized `(name, role)`;
* subjects are deduplicated case-insensitively after trimming while preserving first emitted spelling;
* result validates against schema.

---

### Fixture F007: EPUB with ambiguous author string

**Purpose:**
Verify uncertain author splitting.

**Generation rule:**
Generate dynamically with `ebooklib` or hand-crafted OPF.

**Output file:**

`tmp/epubs/ambiguous_author.epub`

**EPUB metadata:**

```json
{
  "identifier": {
    "scheme": "Test",
    "value": "TEST-007"
  },
  "title": "Ambiguous Author Book",
  "language": "en",
  "authors": [
    "Smith, John, editor"
  ]
}
```

**Content:**

`OEBPS/chapter_1.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Chapter One</title>
  </head>
  <body>
    <h1>Chapter One</h1>
    <p>This generated book has an ambiguous creator string.</p>
  </body>
</html>
```

**Config:**
Use fixture F000.

**Expected reusable assertions:**

* extraction succeeds;
* ambiguous author string is not split solely on commas;
* `book.authors` contains one author-like object preserving the safe creator name string, or otherwise the implementation must emit `metadata_author_split_uncertain`;
* if `metadata_author_split_uncertain` is emitted, severity is `warning`;
* result validates against schema.

**Documentation gap:**
The exact emitted author name after cleanup is not fully specified. Assert no unsafe broad split into several authors based only on commas.

---

### Fixture F008: EPUB with duplicate unresolved footnote markers

**Purpose:**
Verify unresolved duplicate marker behavior.

**Generation rule:**
Generate dynamically with `ebooklib`.

**Output file:**

`tmp/epubs/duplicate_footnotes.epub`

**EPUB metadata:**

```json
{
  "identifier": {
    "scheme": "Test",
    "value": "TEST-008"
  },
  "title": "Duplicate Footnote Marker Book",
  "language": "en",
  "authors": [
    "Footnote Tester"
  ]
}
```

**Content:**

`OEBPS/chapter_1.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Chapter One</title>
  </head>
  <body>
    <h1>Chapter One</h1>
    <p>First paragraph with an ambiguous star marker * in the text.</p>
    <p>Second paragraph with another ambiguous star marker * in the same chapter.</p>
    <p>* First possible note.</p>
    <p>* Second possible note.</p>
  </body>
</html>
```

**Config:**
Use fixture F000.

**Expected reusable assertions:**

* extraction succeeds;
* ambiguous plain `*` markers remain in paragraph text unless uniquely linked;
* diagnostics contain `footnote_duplicate_marker` with severity `warning` or `footnote_marker_unresolved` with severity `warning`;
* implementation must not silently remove both `*` markers without a confidently resolved footnote link;
* result validates against schema.

---

### Fixture F009: EPUB with oversized HTML plus valid fallback chapter

**Purpose:**
Verify non-fatal skip of one oversized HTML document.

**Generation rule:**
Generate dynamically with `ebooklib`.

**Output file:**

`tmp/epubs/oversized_html_with_fallback.epub`

**EPUB metadata:**

```json
{
  "identifier": {
    "scheme": "Test",
    "value": "TEST-009"
  },
  "title": "Oversized HTML Book",
  "language": "en",
  "authors": [
    "Limit Tester"
  ]
}
```

**Spine / reading order:**

```json
[
  "nav",
  "oversized.xhtml",
  "chapter_ok.xhtml"
]
```

**Content:**

`OEBPS/oversized.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Oversized</title>
  </head>
  <body>
    <p>XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</p>
  </body>
</html>
```

`OEBPS/chapter_ok.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Readable Chapter</title>
  </head>
  <body>
    <h1>Readable Chapter</h1>
    <p>This chapter remains below the configured HTML size limit.</p>
  </body>
</html>
```

**Config:**

```json
{
  "include_front_matter_in_canonical_text": false,
  "include_back_matter_in_canonical_text": false,
  "include_footnotes_in_canonical_text": false,
  "include_chapter_titles_in_canonical_text": true,
  "include_section_titles_in_canonical_text": false,
  "max_epub_size_bytes": 104857600,
  "max_html_document_size_bytes": 200,
  "max_text_block_chars": 100000,
  "pipeline_timeout_seconds": 120,
  "html_parse_timeout_seconds": 20,
  "max_archive_uncompressed_bytes": 524288000,
  "max_archive_entry_count": 10000,
  "max_archive_compression_ratio": 100,
  "max_toc_depth": 8,
  "max_diagnostic_count": 1000,
  "max_output_json_bytes": 524288000,
  "include_debug": false
}
```

**Expected reusable assertions:**

* extraction succeeds if `chapter_ok.xhtml` remains readable;
* diagnostics contain `html_document_too_large_skipped` with severity `warning`;
* skipped oversized content is not partially emitted;
* `book.chapters` contains readable text from `chapter_ok.xhtml`;
* result validates against schema.

---

### Fixture F010: Valid EPUB with only oversized HTML documents

**Purpose:**
Verify failure when all readable content is skipped.

**Generation rule:**
Generate dynamically with `ebooklib`.

**Output file:**

`tmp/epubs/all_oversized_html.epub`

**EPUB metadata:**

```json
{
  "identifier": {
    "scheme": "Test",
    "value": "TEST-010"
  },
  "title": "All Oversized Book",
  "language": "en",
  "authors": [
    "Limit Tester"
  ]
}
```

**Content:**

`OEBPS/oversized.xhtml`

```html
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Oversized Only</title>
  </head>
  <body>
    <p>YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY</p>
  </body>
</html>
```

**Config:**

```json
{
  "include_front_matter_in_canonical_text": false,
  "include_back_matter_in_canonical_text": false,
  "include_footnotes_in_canonical_text": false,
  "include_chapter_titles_in_canonical_text": true,
  "include_section_titles_in_canonical_text": false,
  "max_epub_size_bytes": 104857600,
  "max_html_document_size_bytes": 50,
  "max_text_block_chars": 100000,
  "pipeline_timeout_seconds": 120,
  "html_parse_timeout_seconds": 20,
  "max_archive_uncompressed_bytes": 524288000,
  "max_archive_entry_count": 10000,
  "max_archive_compression_ratio": 100,
  "max_toc_depth": 8,
  "max_diagnostic_count": 1000,
  "max_output_json_bytes": 524288000,
  "include_debug": false
}
```

**Expected reusable assertions:**

* extraction fails;
* `status = "failed"`;
* `error.code = "no_readable_content"`;
* `error.recoverable = false`;
* `book` is absent;
* diagnostics contain `html_document_too_large_skipped` with severity `warning`;
* diagnostics may contain `empty_readable_content` with severity `error` if extraction reaches content analysis;
* result validates against schema.

---

### Fixture F011: Plain text file with `.epub` extension

**Purpose:**
Verify non-ZIP input rejection.

**File:**

`tmp/epubs/plain_text.epub`

**Encoding:**
UTF-8.

**Content:**

```text
This is not a ZIP archive and not a valid EPUB.
```

**Config:**
Use fixture F000.

**Expected reusable assertions:**

* extraction fails;
* `error.code = "input_not_epub"`;
* `book` is absent;
* result validates against schema.

---

### Fixture F012: Valid ZIP but not EPUB

**Purpose:**
Verify ZIP container without EPUB package metadata maps to manifest unreadable.

**Generation rule:**
Generate dynamically with `zipfile`.

**File:**

`tmp/epubs/zip_not_epub.epub`

**ZIP entries:**

`README.txt`

```text
This ZIP opens successfully but has no META-INF/container.xml and no OPF package.
```

**Config:**
Use fixture F000.

**Expected reusable assertions:**

* extraction fails;
* `error.code = "epub_manifest_unreadable"`;
* archive security diagnostics are absent unless the implementation detects a separate archive violation;
* result validates against schema.

---

### Fixture F013: ZIP with path traversal archive entry

**Purpose:**
Verify archive safety precedence.

**Generation rule:**
Generate dynamically with `zipfile`; do not use `ebooklib`.

**File:**

`tmp/epubs/path_traversal.epub`

**ZIP entries:**

`../evil.txt`

```text
This archive entry escapes the EPUB root.
```

`README.txt`

```text
This archive intentionally lacks valid EPUB metadata too.
```

**Config:**
Use fixture F000.

**Expected reusable assertions:**

* extraction fails;
* `error.code = "epub_archive_security_violation"`;
* this error takes precedence over `epub_manifest_unreadable`;
* no OPF/HTML parsing should be required before failure;
* result validates against schema.

---

### Fixture F014: ZIP with excessive entry count

**Purpose:**
Verify `max_archive_entry_count`.

**Generation rule:**
Generate dynamically with `zipfile`.

**File:**

`tmp/epubs/too_many_entries.epub`

**ZIP entries:**

```json
[
  {
    "path": "file_001.txt",
    "content": "one"
  },
  {
    "path": "file_002.txt",
    "content": "two"
  },
  {
    "path": "file_003.txt",
    "content": "three"
  },
  {
    "path": "file_004.txt",
    "content": "four"
  }
]
```

**Config:**

```json
{
  "include_front_matter_in_canonical_text": false,
  "include_back_matter_in_canonical_text": false,
  "include_footnotes_in_canonical_text": false,
  "include_chapter_titles_in_canonical_text": true,
  "include_section_titles_in_canonical_text": false,
  "max_epub_size_bytes": 104857600,
  "max_html_document_size_bytes": 10485760,
  "max_text_block_chars": 100000,
  "pipeline_timeout_seconds": 120,
  "html_parse_timeout_seconds": 20,
  "max_archive_uncompressed_bytes": 524288000,
  "max_archive_entry_count": 3,
  "max_archive_compression_ratio": 100,
  "max_toc_depth": 8,
  "max_diagnostic_count": 1000,
  "max_output_json_bytes": 524288000,
  "include_debug": false
}
```

**Expected reusable assertions:**

* extraction fails;
* `error.code = "epub_archive_security_violation"`;
* result validates against schema.

---

### Fixture F015: ZIP with excessive compression ratio

**Purpose:**
Verify ZIP bomb guard.

**Generation rule:**
Generate dynamically with `zipfile` using compression enabled.

**File:**

`tmp/epubs/high_compression_ratio.epub`

**ZIP entries:**

`repeated.txt`

```text
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
```

**Config:**

```json
{
  "include_front_matter_in_canonical_text": false,
  "include_back_matter_in_canonical_text": false,
  "include_footnotes_in_canonical_text": false,
  "include_chapter_titles_in_canonical_text": true,
  "include_section_titles_in_canonical_text": false,
  "max_epub_size_bytes": 104857600,
  "max_html_document_size_bytes": 10485760,
  "max_text_block_chars": 100000,
  "pipeline_timeout_seconds": 120,
  "html_parse_timeout_seconds": 20,
  "max_archive_uncompressed_bytes": 524288000,
  "max_archive_entry_count": 10000,
  "max_archive_compression_ratio": 1,
  "max_toc_depth": 8,
  "max_diagnostic_count": 1000,
  "max_output_json_bytes": 524288000,
  "include_debug": false
}
```

**Expected reusable assertions:**

* if the compressed entry ratio is greater than `1`, extraction fails with `epub_archive_security_violation`;
* if the test environment ZIP compressor does not produce ratio greater than `1`, the generated fixture is invalid and must be enlarged until ratio exceeds configured limit;
* result validates against schema.

---

### Fixture F016: Invalid config with unknown field

**Purpose:**
Verify config schema closure and validation precedence.

**Input path:**
Use intentionally missing path:

`tmp/epubs/does_not_exist.epub`

**Config:**

```json
{
  "unknown_field": true
}
```

**Expected reusable assertions:**

* library returns structured failed result;
* `error.code = "invalid_config"`;
* input path validation must not run;
* result must not return `input_file_not_found`;
* `extraction.config` contains default effective config snapshot from F000;
* raw invalid config field is absent from production output;
* result validates against schema.

---

### Fixture F017: Invalid config with wrong numeric type

**Purpose:**
Verify numeric config values must be JSON integers, not strings or floats.

**Input path:**
Use valid EPUB fixture F001.

**Config:**

```json
{
  "max_epub_size_bytes": "100MB"
}
```

**Expected reusable assertions:**

* extraction fails before EPUB parsing;
* `error.code = "invalid_config"`;
* `error.recoverable = false`;
* `book` is absent;
* `extraction.config` equals default effective config snapshot from F000;
* result validates against schema.

---

### Fixture F018: Config with `$schema` tooling field

**Purpose:**
Verify `$schema` is accepted as input-only config field and omitted from output config.

**Input path:**
Use fixture F001.

**Config:**

```json
{
  "$schema": "https://schemas.deszo.local/schema/epub_content_extractor_config.v2.2.schema.json",
  "include_chapter_titles_in_canonical_text": false
}
```

**Expected reusable assertions:**

* extraction succeeds;
* `extraction.config.include_chapter_titles_in_canonical_text = false`;
* `extraction.config` does not contain `$schema`;
* `$schema` does not appear anywhere in production output except possibly debug if explicitly allowed and redacted;
* result validates against schema.

---

### Fixture F019: Valid max-boundary config

**Purpose:**
Verify hard maximum boundary values are accepted.

**Input path:**
Use fixture F001.

**Config:**

```json
{
  "include_front_matter_in_canonical_text": true,
  "include_back_matter_in_canonical_text": true,
  "include_footnotes_in_canonical_text": true,
  "include_chapter_titles_in_canonical_text": false,
  "include_section_titles_in_canonical_text": true,
  "max_epub_size_bytes": 1073741824,
  "max_html_document_size_bytes": 104857600,
  "max_text_block_chars": 1000000,
  "pipeline_timeout_seconds": 3600,
  "html_parse_timeout_seconds": 300,
  "max_archive_uncompressed_bytes": 2147483648,
  "max_archive_entry_count": 100000,
  "max_archive_compression_ratio": 1000,
  "max_toc_depth": 64,
  "max_diagnostic_count": 100000,
  "max_output_json_bytes": 1073741824,
  "include_debug": false
}
```

**Expected reusable assertions:**

* config is accepted;
* extraction succeeds for F001;
* `extraction.config` equals the supplied config;
* result validates against schema.

---

### Fixture F020: Config above hard maximum

**Purpose:**
Verify hard maximum violations fail config validation.

**Input path:**
Use fixture F001.

**Config:**

```json
{
  "max_toc_depth": 65
}
```

**Expected reusable assertions:**

* extraction fails before EPUB parsing;
* `error.code = "invalid_config"`;
* `book` is absent;
* result validates against schema.

---

### Fixture F021: Valid EPUB with output file size above configured input limit

**Purpose:**
Verify `max_epub_size_bytes` is enforced before opening EPUB.

**Input path:**
Use fixture F001, whose generated file size must be greater than `1` byte.

**Config:**

```json
{
  "include_front_matter_in_canonical_text": false,
  "include_back_matter_in_canonical_text": false,
  "include_footnotes_in_canonical_text": false,
  "include_chapter_titles_in_canonical_text": true,
  "include_section_titles_in_canonical_text": false,
  "max_epub_size_bytes": 1,
  "max_html_document_size_bytes": 10485760,
  "max_text_block_chars": 100000,
  "pipeline_timeout_seconds": 120,
  "html_parse_timeout_seconds": 20,
  "max_archive_uncompressed_bytes": 524288000,
  "max_archive_entry_count": 10000,
  "max_archive_compression_ratio": 100,
  "max_toc_depth": 8,
  "max_diagnostic_count": 1000,
  "max_output_json_bytes": 524288000,
  "include_debug": false
}
```

**Expected reusable assertions:**

* extraction fails;
* `error.code = "epub_file_too_large"`;
* failure happens before ZIP parsing;
* result validates against schema.

---

### Fixture F022: Canonical text builder book object

**Purpose:**
Pure fixture for `build_canonical_text`.

**Input object:**

```json
{
  "title": "Builder Test Book",
  "subtitle": null,
  "language": "en",
  "authors": [
    {
      "name": "Builder Author",
      "role": "author"
    }
  ],
  "contributors": [],
  "metadata": {
    "identifiers": [],
    "publisher": null,
    "published_at": null,
    "modified_at": null,
    "description": null,
    "rights": null,
    "subjects": [],
    "source_file": {
      "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "size_bytes": 123
    }
  },
  "front_matter": [
    {
      "id": "front_001",
      "type": "preface",
      "title": "Preface",
      "text": "Front matter paragraph.",
      "paragraphs": [
        {
          "text": "Front matter paragraph."
        }
      ],
      "footnotes": [],
      "included_in_canonical_text": false
    }
  ],
  "chapters": [
    {
      "id": "chapter_001",
      "chapter_number": 1,
      "type": "chapter",
      "title": "Chapter One",
      "text": "First chapter paragraph.\n\nSecond chapter paragraph.",
      "paragraphs": [
        {
          "text": "First chapter paragraph."
        },
        {
          "text": "Second chapter paragraph."
        }
      ],
      "footnotes": [
        {
          "id": "footnote_001",
          "marker": "1",
          "text": "Chapter footnote text.",
          "paragraph_number": 1
        }
      ]
    }
  ],
  "back_matter": [
    {
      "id": "back_001",
      "type": "appendix",
      "title": "Appendix",
      "text": "Back matter paragraph.",
      "paragraphs": [
        {
          "text": "Back matter paragraph."
        }
      ],
      "footnotes": [],
      "included_in_canonical_text": false
    }
  ],
  "footnotes": [],
  "table_of_contents": [],
  "assets": []
}
```

**Default builder options:**

```json
{
  "include_front_matter": false,
  "include_back_matter": false,
  "include_footnotes": false,
  "include_chapter_titles": true,
  "include_section_titles": false,
  "separator_between_paragraphs": "\n\n",
  "separator_between_chapters": "\n\n\n"
}
```

**Expected reusable assertions:**

* default canonical text equals:

```text
Chapter One

First chapter paragraph.

Second chapter paragraph.
```

* custom inclusion options affect text deterministically;
* builder must not mutate input object.

---

## 5. Test Case Matrix

| ID     | Category                        | Purpose                                       | Input fixture                 | Expected result                             | Priority |
| ------ | ------------------------------- | --------------------------------------------- | ----------------------------- | ------------------------------------------- | -------- |
| TC-001 | Valid minimal input             | Library happy path with generated EPUB        | F001                          | success + schema valid                      | P0       |
| TC-002 | Valid CLI input                 | CLI stdout extraction                         | F001                          | exit `0` + JSON success                     | P0       |
| TC-003 | Output schema                   | Success result contract validation            | F001                          | validates against result schema             | P0       |
| TC-004 | Config defaults                 | Missing config applies defaults               | F001 + F000                   | output config equals F000                   | P0       |
| TC-005 | Config input-only field         | `$schema` accepted and omitted                | F018                          | success; no `$schema` in snapshot           | P0       |
| TC-006 | Invalid config unknown field    | Closed config schema                          | F016                          | `invalid_config`, no path validation        | P0       |
| TC-007 | Invalid config wrong type       | String numeric config rejected                | F017                          | `invalid_config`                            | P0       |
| TC-008 | Config boundary                 | Hard maximums accepted                        | F019                          | success                                     | P1       |
| TC-009 | Config boundary invalid         | Above hard maximum rejected                   | F020                          | `invalid_config`                            | P1       |
| TC-010 | Missing input path              | Missing file error                            | missing path + F000           | `input_file_not_found`                      | P0       |
| TC-011 | Directory input                 | Non-file path error                           | temp directory + F000         | `input_not_file`                            | P0       |
| TC-012 | Programmer error                | `input_path = None` raises                    | direct API call               | `TypeError`                                 | P0       |
| TC-013 | Non-EPUB input                  | Plain text `.epub` rejected                   | F011                          | `input_not_epub`                            | P0       |
| TC-014 | ZIP not EPUB                    | Openable ZIP without OPF                      | F012                          | `epub_manifest_unreadable`                  | P0       |
| TC-015 | Archive traversal               | Unsafe ZIP path precedence                    | F013                          | `epub_archive_security_violation`           | P0       |
| TC-016 | Archive entry limit             | Too many ZIP entries                          | F014                          | `epub_archive_security_violation`           | P1       |
| TC-017 | Archive compression ratio       | ZIP bomb guard                                | F015                          | `epub_archive_security_violation`           | P1       |
| TC-018 | EPUB file size limit            | File too large before parse                   | F021                          | `epub_file_too_large`                       | P0       |
| TC-019 | Missing metadata                | Non-fatal metadata diagnostics                | F003                          | success + metadata diagnostics              | P0       |
| TC-020 | Language contract               | Non-English metadata warning                  | F004                          | success, `book.language = "en"`             | P0       |
| TC-021 | Invalid date                    | Date normalized to null                       | F005                          | success + `metadata_date_invalid`           | P1       |
| TC-022 | Duplicate metadata              | Deduplicate metadata values                   | F006                          | success + deduplicated arrays               | P1       |
| TC-023 | Ambiguous author                | Avoid unsafe comma split                      | F007                          | success + safe author handling              | P1       |
| TC-024 | Complex EPUB                    | Chapters, sections, TOC, assets               | F002                          | success + invariants                        | P1       |
| TC-025 | Footnote ambiguity              | Duplicate markers not silently removed        | F008                          | success + warning diagnostic                | P1       |
| TC-026 | Oversized HTML skip             | One oversized HTML skipped, fallback succeeds | F009                          | success + warning                           | P1       |
| TC-027 | No readable content after skip  | All readable content skipped                  | F010                          | `no_readable_content`                       | P0       |
| TC-028 | Canonical builder default       | Default canonical text                        | F022                          | exact text                                  | P0       |
| TC-029 | Canonical builder invalid input | Builder programmer errors                     | invalid book/options          | `TypeError`/`ValueError`                    | P0       |
| TC-030 | Determinism                     | Repeated library run stable                   | F001                          | equal after volatile normalization          | P0       |
| TC-031 | CLI pretty mode                 | Pretty and compact JSON equal semantically    | F001                          | parsed objects equal except volatile fields | P1       |
| TC-032 | CLI invalid config from file    | CLI exit-code mapping                         | F017 as config file           | exit `4` + JSON failed result               | P0       |
| TC-033 | CLI parser error                | Invalid CLI option                            | no fixture                    | exit `2`, no JSON                           | P0       |
| TC-034 | CLI output write failure        | No stdout fallback                            | F001 + unwritable output path | exit `3`, no JSON fallback                  | P1       |
| TC-035 | Debug disabled                  | No top-level debug by default                 | F001                          | `debug` absent                              | P0       |
| TC-036 | Debug enabled                   | Debug allowed but semantics unchanged         | F001 + include_debug true     | success, production fields stable           | P1       |
| TC-037 | Diagnostic registry             | All emitted diagnostics documented            | all integration fixtures      | code/severity matrix valid                  | P0       |
| TC-038 | Failed result shape             | No partial book on failure                    | negative fixtures             | `book` absent, `error` present              | P0       |
| TC-039 | Privacy/path safety             | No absolute local paths in production output  | all fixtures                  | no temp root path leaked                    | P0       |
| TC-040 | Schema/docs drift               | Synthetic invalid schema cases rejected       | schema-only objects           | schema rejects invalid result shapes        | P0       |

---

## 6. Detailed Test Cases

## TC-001: Library extracts minimal generated EPUB

**Category:**
Valid / Integration / Contract

**Priority:**
P0

**Source requirement:**
The public library function accepts a local `.epub` path and optional config, returns a plain JSON-serializable mapping, and succeeds for a valid English EPUB with readable content.

**Purpose:**
Verify the basic library happy path using a dynamically generated EPUB.

**Preconditions:**

* Create a temporary directory.
* Generate fixture F001 into `tmp/epubs/minimal_valid.epub`.
* Load official result schema `schema/epub_content_extractor.v2.2.schema.json`.

**Input data:**
Generated EPUB fixture F001.

**Config:**
Use missing config or `{}`.

**Execution steps:**

1. Call `extract_epub_content("tmp/epubs/minimal_valid.epub", config=None)`.
2. Capture returned mapping.
3. Validate returned mapping against official result schema.

**Expected result:**

* `status = "succeeded"`;
* `schema_version = "epub_content_extractor.v2.2"`;
* `book` exists;
* `error` is absent;
* `book.language = "en"`;
* `book.title = "Minimal Test Book"`;
* `book.authors[0].name = "Jane Example"`;
* `book.authors[0].role = "author"`;
* at least one readable chapter exists;
* no diagnostic has `severity = "error"`;
* result validates against schema.

**Expected assertions:**

* `assert result["status"] == "succeeded"`
* `assert result["schema_version"] == "epub_content_extractor.v2.2"`
* `assert "book" in result`
* `assert "error" not in result`
* `assert result["book"]["language"] == "en"`
* `assert result validates against schema/epub_content_extractor.v2.2.schema.json`
* `assert all(d["severity"] != "error" for d in result["diagnostics"])`

**Automation notes:**
Use `ebooklib` to generate the EPUB before calling the extractor. Do not commit the generated `.epub`.

**Ambiguities:**
None.

---

## TC-002: CLI extracts minimal generated EPUB to stdout

**Category:**
Valid / CLI / Contract

**Priority:**
P0

**Source requirement:**
CLI command `epub-content-extractor extract INPUT.epub` writes the structured result JSON to stdout when `--output` is omitted and exits `0` on successful extraction.

**Purpose:**
Verify CLI happy path and stdout JSON contract.

**Preconditions:**

* Generate fixture F001.
* Ensure CLI executable is available in test environment.

**Input data:**
`tmp/epubs/minimal_valid.epub`.

**Config:**
No `--config` argument.

**Execution steps:**

1. Run:

```bash
epub-content-extractor extract tmp/epubs/minimal_valid.epub
```

2. Capture exit code, stdout, stderr.
3. Parse stdout as JSON.
4. Validate parsed JSON against result schema.

**Expected result:**

* process exit code is `0`;
* stdout is valid JSON result object;
* stderr is empty or contains no required machine-readable data;
* parsed JSON has `status = "succeeded"`;
* parsed JSON validates against schema.

**Expected assertions:**

* `assert exit_code == 0`
* `assert stdout parses as JSON`
* `assert parsed["status"] == "succeeded"`
* `assert parsed validates against schema/epub_content_extractor.v2.2.schema.json`

**Automation notes:**
Do not assert exact whitespace. Compare parsed JSON.

**Ambiguities:**
None.

---

## TC-003: Successful result validates against official result schema

**Category:**
Contract / Schema validation

**Priority:**
P0

**Source requirement:**
Representative production outputs must validate against the official result JSON Schema.

**Purpose:**
Catch schema/docs drift and invalid production output.

**Preconditions:**

* Generate fixture F001.
* Load official schema.

**Input data:**
Generated EPUB fixture F001.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run library extraction.
2. Validate result against official schema.

**Expected result:**

* schema validation passes;
* no additional top-level properties are present;
* success branch of schema is selected;
* `book` is required and present;
* `error` is absent.

**Expected assertions:**

* `assert schema_validation(result) passes`
* `assert set(result.keys()) <= {"schema_version", "status", "book", "diagnostics", "extraction", "debug"}`
* `assert "book" in result`
* `assert "error" not in result`

**Automation notes:**
Use a Draft 2020-12 compatible JSON Schema validator.

**Ambiguities:**
None.

---

## TC-004: Missing config applies default effective config

**Category:**
Config validation / Contract

**Priority:**
P0

**Source requirement:**
A missing config is equivalent to `{}` and must use documented default effective config.

**Purpose:**
Verify config default application and output snapshot.

**Preconditions:**
Generate fixture F001.

**Input data:**
Generated EPUB fixture F001.

**Config:**
`None`.

**Execution steps:**

1. Run library extraction with `config=None`.
2. Read `result.extraction.config`.

**Expected result:**

`result.extraction.config` exactly equals fixture F000.

**Expected assertions:**

* `assert result["status"] == "succeeded"`
* `assert result["extraction"]["config"] == F000`
* `assert "$schema" not in result["extraction"]["config"]`

**Automation notes:**
Compare the full config object, not only a subset.

**Ambiguities:**
None.

---

## TC-005: `$schema` input config field is accepted but omitted from output config

**Category:**
Config validation / Contract

**Priority:**
P0

**Source requirement:**
Input config may include optional tooling-only `$schema` URI. It must be ignored semantically and omitted from `extraction.config`.

**Purpose:**
Verify tooling metadata does not affect semantic output.

**Preconditions:**
Generate fixture F001.

**Input data:**
Generated EPUB fixture F001.

**Config:**
Use fixture F018.

**Execution steps:**

1. Run library extraction with config from F018.
2. Inspect `result.extraction.config`.
3. Search production output for `$schema`.

**Expected result:**

* extraction succeeds;
* `extraction.config.include_chapter_titles_in_canonical_text = false`;
* `"$schema"` absent from `extraction.config`;
* result validates against schema.

**Expected assertions:**

* `assert result["status"] == "succeeded"`
* `assert result["extraction"]["config"]["include_chapter_titles_in_canonical_text"] is False`
* `assert "$schema" not in result["extraction"]["config"]`
* `assert result validates against schema`

**Automation notes:**
Do not assert that canonical text length changes here; that belongs to builder/config-specific tests.

**Ambiguities:**
None.

---

## TC-006: Unknown config field fails before input path validation

**Category:**
Invalid config / Precedence

**Priority:**
P0

**Source requirement:**
Config schema is closed. Unknown config fields are invalid. Config validation happens before input path validation and EPUB parsing.

**Purpose:**
Verify error precedence and prevent accidental parsing with invalid config.

**Preconditions:**
Do not create the input file.

**Input data:**

`tmp/epubs/does_not_exist.epub` must not exist.

**Config:**

```json
{
  "unknown_field": true
}
```

**Execution steps:**

1. Call library extraction with the missing path and invalid config.
2. Inspect failed result.

**Expected result:**

* `status = "failed"`;
* `error.code = "invalid_config"`;
* `error.recoverable = false`;
* `book` absent;
* `error.code` is not `input_file_not_found`;
* `extraction.config` equals F000 default snapshot;
* result validates against schema.

**Expected assertions:**

* `assert result["status"] == "failed"`
* `assert result["error"]["code"] == "invalid_config"`
* `assert result["error"]["recoverable"] is False`
* `assert "book" not in result`
* `assert result["extraction"]["config"] == F000`
* `assert result validates against schema`

**Automation notes:**
This is a critical precedence regression test.

**Ambiguities:**
None.

---

## TC-007: String numeric config value is rejected

**Category:**
Invalid config / Type validation

**Priority:**
P0

**Source requirement:**
Numeric config values must be JSON numbers with integer values. String units such as `"100MB"` are invalid.

**Purpose:**
Verify strict numeric config typing.

**Preconditions:**
Generate fixture F001.

**Input data:**
Generated EPUB fixture F001.

**Config:**

```json
{
  "max_epub_size_bytes": "100MB"
}
```

**Execution steps:**

1. Call library extraction with F001 and invalid config.
2. Inspect result.

**Expected result:**

* `status = "failed"`;
* `error.code = "invalid_config"`;
* EPUB parsing does not start;
* production output does not contain raw invalid config string `"100MB"`;
* result validates against schema.

**Expected assertions:**

* `assert result["error"]["code"] == "invalid_config"`
* `assert "book" not in result`
* `assert "100MB" not in serialized_production_result`
* `assert result validates against schema`

**Automation notes:**
Serialize result to JSON and search for raw invalid config value.

**Ambiguities:**
None.

---

## TC-008: Hard maximum config values are accepted

**Category:**
Boundary / Config validation

**Priority:**
P1

**Source requirement:**
Resource limit fields have hard schema maximums. Values equal to the maximum are valid.

**Purpose:**
Verify inclusive maximum boundary.

**Preconditions:**
Generate fixture F001.

**Input data:**
Generated EPUB fixture F001.

**Config:**
Use fixture F019.

**Execution steps:**

1. Run library extraction with F019 config.
2. Inspect `extraction.config`.

**Expected result:**

* extraction succeeds;
* every supplied maximum value is preserved in `extraction.config`;
* result validates against schema.

**Expected assertions:**

* `assert result["status"] == "succeeded"`
* `assert result["extraction"]["config"] == F019.config`
* `assert result validates against schema`

**Automation notes:**
This should not create a huge EPUB; only config values are large.

**Ambiguities:**
None.

---

## TC-009: Config value above hard maximum is rejected

**Category:**
Boundary / Invalid config

**Priority:**
P1

**Source requirement:**
Values above hard schema maximums are invalid config.

**Purpose:**
Verify exclusive upper bound rejection.

**Preconditions:**
Generate fixture F001.

**Input data:**
Generated EPUB fixture F001.

**Config:**

```json
{
  "max_toc_depth": 65
}
```

**Execution steps:**

1. Run library extraction with invalid config.
2. Inspect failed result.

**Expected result:**

* `status = "failed"`;
* `error.code = "invalid_config"`;
* `book` absent;
* result validates against schema.

**Expected assertions:**

* `assert result["error"]["code"] == "invalid_config"`
* `assert "book" not in result`
* `assert result validates against schema`

**Automation notes:**
No EPUB parsing should be required.

**Ambiguities:**
None.

---

## TC-010: Missing input file returns `input_file_not_found`

**Category:**
Invalid input / Filesystem

**Priority:**
P0

**Source requirement:**
If input path does not exist, extraction fails with `input_file_not_found`.

**Purpose:**
Verify missing file behavior.

**Preconditions:**

* Ensure `tmp/epubs/missing.epub` does not exist.
* Config is valid.

**Input data:**

`tmp/epubs/missing.epub`

**Config:**
Use fixture F000.

**Execution steps:**

1. Call library extraction with missing path.
2. Inspect result.

**Expected result:**

* `status = "failed"`;
* `error.code = "input_file_not_found"`;
* `error.recoverable = false`;
* `book` absent;
* summary counts are zero except `error_count = 1`;
* result validates against schema.

**Expected assertions:**

* `assert result["error"]["code"] == "input_file_not_found"`
* `assert result["extraction"]["summary"]["error_count"] == 1`
* `assert "book" not in result`
* `assert result validates against schema`

**Automation notes:**
Use a temp path that was never created.

**Ambiguities:**
None.

---

## TC-011: Directory input returns `input_not_file`

**Category:**
Invalid input / Filesystem

**Priority:**
P0

**Source requirement:**
If input path exists but is not a regular file, extraction fails with `input_not_file`.

**Purpose:**
Verify non-file path rejection.

**Preconditions:**
Create directory `tmp/epubs/not_a_file.epub/`.

**Input data:**

`tmp/epubs/not_a_file.epub/`

**Config:**
Use fixture F000.

**Execution steps:**

1. Call library extraction with directory path.
2. Inspect result.

**Expected result:**

* `status = "failed"`;
* `error.code = "input_not_file"`;
* `book` absent;
* result validates against schema.

**Expected assertions:**

* `assert result["error"]["code"] == "input_not_file"`
* `assert "book" not in result`
* `assert result validates against schema`

**Automation notes:**
On Windows and POSIX this should be stable.

**Ambiguities:**
None.

---

## TC-012: `input_path = None` raises `TypeError`

**Category:**
Programmer error / API

**Priority:**
P0

**Source requirement:**
`input_path = None` or non-`str`/non-`Path` is a programmer error and must raise `TypeError`, not return an extraction result.

**Purpose:**
Verify programmer-error policy.

**Preconditions:**
None.

**Input data:**

```json
{
  "input_path": null,
  "config": null
}
```

**Config:**
None.

**Execution steps:**

1. Call `extract_epub_content(None, config=None)`.
2. Capture raised exception.

**Expected result:**

* `TypeError` is raised;
* no `EpubContentExtractionResult` is returned.

**Expected assertions:**

* `assert raises TypeError`
* `assert no result object is returned`

**Automation notes:**
Do not catch and convert this to failed result.

**Ambiguities:**
None.

---

## TC-013: Plain text `.epub` returns `input_not_epub`

**Category:**
Invalid input / Malformed input

**Priority:**
P0

**Source requirement:**
If the file cannot be opened as a ZIP-based EPUB container, fail with `input_not_epub`.

**Purpose:**
Verify non-ZIP rejection.

**Preconditions:**
Create fixture F011.

**Input data:**
`tmp/epubs/plain_text.epub` containing UTF-8 text, not ZIP bytes.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run library extraction.
2. Inspect result.

**Expected result:**

* `status = "failed"`;
* `error.code = "input_not_epub"`;
* `book` absent;
* result validates against schema.

**Expected assertions:**

* `assert result["error"]["code"] == "input_not_epub"`
* `assert "book" not in result`
* `assert result validates against schema`

**Automation notes:**
Do not generate this file with `ebooklib`.

**Ambiguities:**
None.

---

## TC-014: Valid ZIP without EPUB package returns `epub_manifest_unreadable`

**Category:**
Invalid input / EPUB manifest

**Priority:**
P0

**Source requirement:**
A valid ZIP file that is not a valid EPUB container maps to `epub_manifest_unreadable` when ZIP opens and archive safety checks pass.

**Purpose:**
Verify manifest validation after archive safety.

**Preconditions:**
Create fixture F012.

**Input data:**
ZIP containing only `README.txt`.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run library extraction.
2. Inspect result.

**Expected result:**

* `status = "failed"`;
* `error.code = "epub_manifest_unreadable"`;
* `book` absent;
* result validates against schema.

**Expected assertions:**

* `assert result["error"]["code"] == "epub_manifest_unreadable"`
* `assert result validates against schema`

**Automation notes:**
This verifies that the extractor does not accept arbitrary ZIP files as EPUB.

**Ambiguities:**
None.

---

## TC-015: Path traversal archive entry fails with archive security violation

**Category:**
Security / Archive safety / Regression

**Priority:**
P0

**Source requirement:**
Archive safety checks must reject entries whose normalized path escapes the EPUB root. Archive security violation has precedence over missing/unreadable manifest.

**Purpose:**
Verify path traversal rejection and failure precedence.

**Preconditions:**
Create fixture F013 with ZIP entry `../evil.txt`.

**Input data:**
`tmp/epubs/path_traversal.epub`.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run library extraction.
2. Inspect failed result.

**Expected result:**

* `status = "failed"`;
* `error.code = "epub_archive_security_violation"`;
* `error.code` is not `epub_manifest_unreadable`;
* `book` absent;
* result validates against schema.

**Expected assertions:**

* `assert result["error"]["code"] == "epub_archive_security_violation"`
* `assert "book" not in result`
* `assert result validates against schema`

**Automation notes:**
Use `zipfile`; valid EPUB libraries may prevent unsafe path creation.

**Ambiguities:**
None.

---

## TC-016: Excessive archive entry count fails with archive security violation

**Category:**
Security / Boundary

**Priority:**
P1

**Source requirement:**
Extractor must enforce `max_archive_entry_count` before parsing content.

**Purpose:**
Verify configured archive entry limit.

**Preconditions:**
Create fixture F014 with 4 ZIP entries.

**Input data:**
`tmp/epubs/too_many_entries.epub`.

**Config:**
Use F014 config with `max_archive_entry_count = 3`.

**Execution steps:**

1. Run library extraction.
2. Inspect result.

**Expected result:**

* `status = "failed"`;
* `error.code = "epub_archive_security_violation"`;
* result validates against schema.

**Expected assertions:**

* `assert result["error"]["code"] == "epub_archive_security_violation"`
* `assert result validates against schema`

**Automation notes:**
Do not include unsafe paths; this test should isolate entry count behavior.

**Ambiguities:**
None.

---

## TC-017: Excessive compression ratio fails with archive security violation

**Category:**
Security / ZIP bomb guard

**Priority:**
P1

**Source requirement:**
Extractor must enforce per-entry and aggregate compression ratio. Ratio exceeds limit when `ratio > max_archive_compression_ratio`.

**Purpose:**
Verify ZIP bomb protection.

**Preconditions:**
Create fixture F015 with compressed repeated content. Ensure generated ratio is greater than configured limit `1`.

**Input data:**
`tmp/epubs/high_compression_ratio.epub`.

**Config:**
Use F015 config.

**Execution steps:**

1. Generate compressed ZIP.
2. Confirm test fixture compression ratio exceeds `1`.
3. Run library extraction.
4. Inspect result.

**Expected result:**

* if fixture ratio exceeds `1`, `status = "failed"`;
* `error.code = "epub_archive_security_violation"`;
* result validates against schema.

**Expected assertions:**

* `assert generated_ratio > 1`
* `assert result["error"]["code"] == "epub_archive_security_violation"`
* `assert result validates against schema`

**Automation notes:**
If compressor does not produce ratio above `1`, enlarge repeated payload until it does.

**Ambiguities:**
None.

---

## TC-018: EPUB file larger than configured input limit fails before ZIP open

**Category:**
Boundary / Resource limit

**Priority:**
P0

**Source requirement:**
`max_epub_size_bytes` is measured in file bytes before EPUB parsing. Exceeding it is fatal with `epub_file_too_large`.

**Purpose:**
Verify input file size limit.

**Preconditions:**

* Generate fixture F001.
* Ensure generated file size is greater than 1 byte.

**Input data:**
`tmp/epubs/minimal_valid.epub`.

**Config:**
Use F021 config with `max_epub_size_bytes = 1`.

**Execution steps:**

1. Run library extraction with F021 config.
2. Inspect result.

**Expected result:**

* `status = "failed"`;
* `error.code = "epub_file_too_large"`;
* `book` absent;
* result validates against schema.

**Expected assertions:**

* `assert actual_file_size > 1`
* `assert result["error"]["code"] == "epub_file_too_large"`
* `assert "book" not in result`
* `assert result validates against schema`

**Automation notes:**
This should fail before ZIP or OPF processing.

**Ambiguities:**
None.

---

## TC-019: Missing metadata is non-fatal and emits diagnostics

**Category:**
Valid input / Diagnostics

**Priority:**
P0

**Source requirement:**
EPUB without title, author, or language metadata is valid. Missing language is non-fatal because output language is fixed to `"en"`.

**Purpose:**
Verify missing metadata diagnostics and fixed language contract.

**Preconditions:**
Generate fixture F003.

**Input data:**
`tmp/epubs/missing_metadata.epub`.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run library extraction.
2. Inspect `book` and diagnostics.

**Expected result:**

* `status = "succeeded"`;
* `book.language = "en"`;
* `book.title = null`;
* `book.authors = []`;
* diagnostics include:

  * `metadata_missing_title`, severity `warning`;
  * `metadata_missing_author`, severity `info`;
  * `metadata_language_missing`, severity `info`;
* no error diagnostics;
* result validates against schema.

**Expected assertions:**

* `assert result["status"] == "succeeded"`
* `assert result["book"]["language"] == "en"`
* `assert result["book"]["title"] is None`
* `assert diagnostic("metadata_missing_title").severity == "warning"`
* `assert diagnostic("metadata_missing_author").severity == "info"`
* `assert diagnostic("metadata_language_missing").severity == "info"`
* `assert all(d["severity"] != "error" for d in result["diagnostics"])`
* `assert result validates against schema`

**Automation notes:**
If `ebooklib` forces metadata, hand-craft the EPUB ZIP.

**Ambiguities:**
None.

---

## TC-020: Non-English metadata language does not change output language

**Category:**
Valid input / Language contract / Diagnostics

**Priority:**
P0

**Source requirement:**
The output book language is always `"en"`. Non-English-like metadata language emits `metadata_language_conflicts_with_contract` warning but extraction still succeeds.

**Purpose:**
Verify language contract and warning.

**Preconditions:**
Generate fixture F004.

**Input data:**
`tmp/epubs/non_english_metadata_language.epub`.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run library extraction.
2. Inspect `book.language` and diagnostics.

**Expected result:**

* `status = "succeeded"`;
* `book.language = "en"`;
* diagnostics include `metadata_language_conflicts_with_contract` with severity `warning`;
* result validates against schema.

**Expected assertions:**

* `assert result["book"]["language"] == "en"`
* `assert diagnostic("metadata_language_conflicts_with_contract").severity == "warning"`
* `assert result validates against schema`

**Automation notes:**
Content language should not be detected or used for output language.

**Ambiguities:**
None.

---

## TC-021: Invalid date metadata is omitted and diagnosed

**Category:**
Valid input / Metadata normalization

**Priority:**
P1

**Source requirement:**
Invalid or unparseable dates are emitted as `null` and produce `metadata_date_invalid` warning.

**Purpose:**
Verify date cleanup and privacy.

**Preconditions:**
Generate fixture F005.

**Input data:**
`tmp/epubs/invalid_date.epub`.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run extraction.
2. Inspect metadata and serialized production output.

**Expected result:**

* `status = "succeeded"`;
* `book.metadata.published_at = null`;
* diagnostics include `metadata_date_invalid` with severity `warning`;
* raw invalid date string `"not-a-date"` is not emitted in production output;
* result validates against schema.

**Expected assertions:**

* `assert result["book"]["metadata"]["published_at"] is None`
* `assert diagnostic("metadata_date_invalid").severity == "warning"`
* `assert "not-a-date" not in serialized_production_result`
* `assert result validates against schema`

**Automation notes:**
If the generator drops invalid dates before writing OPF, hand-craft the OPF.

**Ambiguities:**
None.

---

## TC-022: Duplicate metadata is deduplicated deterministically

**Category:**
Valid input / Metadata normalization

**Priority:**
P1

**Source requirement:**
Duplicate identifiers, subjects, authors, and contributors must be deduplicated while preserving first-seen order.

**Purpose:**
Verify duplicate metadata cleanup.

**Preconditions:**
Generate fixture F006.

**Input data:**
`tmp/epubs/duplicate_metadata.epub`.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run extraction.
2. Inspect metadata arrays.

**Expected result:**

* extraction succeeds;
* duplicate identifier `(scheme = "Test", value = "DUP-001")` appears once;
* duplicate author `"Repeat Author"` appears once;
* subjects include first spelling of `"Drama"` once and `"Testing"` once;
* result validates against schema.

**Expected assertions:**

* `assert result["status"] == "succeeded"`
* `assert count_identifier("Test", "DUP-001") == 1`
* `assert count_author("Repeat Author", "author") == 1`
* `assert normalized_subjects == ["drama", "testing"]`
* `assert result validates against schema`

**Automation notes:**
Use hand-crafted OPF if needed to force duplicate metadata entries.

**Ambiguities:**
None.

---

## TC-023: Ambiguous comma-separated author is not unsafely split

**Category:**
Valid input / Metadata edge case

**Priority:**
P1

**Source requirement:**
Comma is not a high-confidence author delimiter by itself because it is common in `Last, First` names. If splitting is uncertain, preserve original string as one author and emit `metadata_author_split_uncertain`.

**Purpose:**
Prevent broad overmatching in author splitting.

**Preconditions:**
Generate fixture F007.

**Input data:**
`tmp/epubs/ambiguous_author.epub`.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run extraction.
2. Inspect `book.authors` and diagnostics.

**Expected result:**

* extraction succeeds;
* extractor must not split `"Smith, John, editor"` into multiple authors solely by comma;
* if diagnostic is emitted, it must be `metadata_author_split_uncertain` with severity `warning`;
* result validates against schema.

**Expected assertions:**

* `assert result["status"] == "succeeded"`
* `assert len(result["book"]["authors"]) <= 1 OR diagnostic("metadata_author_split_uncertain") exists`
* `assert no author object has name equal only to "editor"`
* `assert result validates against schema`

**Automation notes:**
This is a regression test against unsafe delimiter splitting.

**Ambiguities:**
Exact preserved name string is not fully specified.

---

## TC-024: Complex generated EPUB preserves structural invariants

**Category:**
Valid complex input / Integration

**Priority:**
P1

**Source requirement:**
Output must preserve structured book data including chapters, front/back matter, TOC, footnotes, and lightweight asset metadata.

**Purpose:**
Verify richer generated EPUB behavior without relying on external book files.

**Preconditions:**
Generate fixture F002.

**Input data:**
`tmp/epubs/complex_valid.epub`.

**Config:**
Use F002 config.

**Execution steps:**

1. Run extraction.
2. Validate schema.
3. Check structural invariants.

**Expected result:**

* extraction succeeds;
* result validates against schema;
* `book.chapters.length >= 2`;
* chapter numbers are `[1, 2, ...]` in reading order;
* required arrays exist even when empty;
* `table_of_contents[].children` exists as array;
* no asset contains binary data or base64 image content;
* summary counts match emitted arrays.

**Expected assertions:**

* `assert result["status"] == "succeeded"`
* `assert len(result["book"]["chapters"]) >= 2`
* `assert chapter_numbers == sorted(chapter_numbers) and first == 1`
* `assert all("children" in toc_item for toc_item in flatten_toc(result["book"]["table_of_contents"]))`
* `assert no "base64" or binary payload fields under book.assets`
* `assert summary.chapter_count == len(book.chapters)`
* `assert result validates against schema`

**Automation notes:**
Do not assert exact section classification unless implementation has deterministic classification for this fixture.

**Ambiguities:**
Exact front/back matter classification may be heuristic.

---

## TC-025: Duplicate unresolved footnote markers are not silently removed

**Category:**
Edge case / Diagnostics / Regression

**Priority:**
P1

**Source requirement:**
Duplicate markers in the same chapter are ambiguous unless unique hyperlink targets disambiguate them. Ambiguous duplicate markers must not be removed silently.

**Purpose:**
Catch false-positive footnote resolution.

**Preconditions:**
Generate fixture F008.

**Input data:**
`tmp/epubs/duplicate_footnotes.epub`.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run extraction.
2. Inspect chapter paragraph text and diagnostics.

**Expected result:**

* extraction succeeds;
* ambiguous `*` markers remain in final paragraph text unless uniquely linked;
* diagnostics contain `footnote_duplicate_marker` or `footnote_marker_unresolved` with severity `warning`;
* no diagnostic severity mismatch;
* result validates against schema.

**Expected assertions:**

* `assert result["status"] == "succeeded"`
* `assert "*" in joined_chapter_paragraph_text OR warning diagnostic exists`
* `assert if diagnostic code is "footnote_duplicate_marker", severity == "warning"`
* `assert if diagnostic code is "footnote_marker_unresolved", severity == "warning"`
* `assert result validates against schema`

**Automation notes:**
This is intentionally invariant-based because exact footnote extraction may vary.

**Ambiguities:**
Exact footnote ownership is heuristic.

---

## TC-026: Oversized HTML document is skipped while fallback content succeeds

**Category:**
Boundary / Partial failure

**Priority:**
P1

**Source requirement:**
If one HTML document exceeds `max_html_document_size_bytes`, it is skipped and emits `html_document_too_large_skipped`; extraction remains non-fatal if readable content remains.

**Purpose:**
Verify non-fatal oversized-document handling.

**Preconditions:**
Generate fixture F009.

**Input data:**
`tmp/epubs/oversized_html_with_fallback.epub`.

**Config:**
Use F009 config.

**Execution steps:**

1. Run extraction.
2. Inspect diagnostics and extracted chapter text.

**Expected result:**

* `status = "succeeded"`;
* diagnostics include `html_document_too_large_skipped` with severity `warning`;
* output contains readable text from `chapter_ok.xhtml`;
* oversized content is not partially emitted;
* result validates against schema.

**Expected assertions:**

* `assert result["status"] == "succeeded"`
* `assert diagnostic("html_document_too_large_skipped").severity == "warning"`
* `assert "This chapter remains below the configured HTML size limit." in all_output_text`
* `assert "XXXXXXXXXXXXXXXX" not in all_output_text`
* `assert result validates against schema`

**Automation notes:**
Configured limit must be lower than `oversized.xhtml` uncompressed byte size and higher than `chapter_ok.xhtml`.

**Ambiguities:**
None.

---

## TC-027: All readable content skipped fails with `no_readable_content`

**Category:**
Negative / Boundary / Contract

**Priority:**
P0

**Source requirement:**
If all readable content is absent, skipped, dropped, or timed out, final result must fail with `no_readable_content`.

**Purpose:**
Prevent false-positive success with empty content.

**Preconditions:**
Generate fixture F010.

**Input data:**
`tmp/epubs/all_oversized_html.epub`.

**Config:**
Use F010 config.

**Execution steps:**

1. Run extraction.
2. Inspect failed result.

**Expected result:**

* `status = "failed"`;
* `error.code = "no_readable_content"`;
* `book` absent;
* diagnostics include `html_document_too_large_skipped` warning;
* diagnostics may include `empty_readable_content` error if extraction reaches content analysis;
* result validates against schema.

**Expected assertions:**

* `assert result["status"] == "failed"`
* `assert result["error"]["code"] == "no_readable_content"`
* `assert "book" not in result`
* `assert diagnostic("html_document_too_large_skipped").severity == "warning"`
* `assert result validates against schema`

**Automation notes:**
Do not assert exact diagnostic count if both warning and error are emitted; assert documented invariants.

**Ambiguities:**
Whether `empty_readable_content` diagnostic is emitted in addition to top-level error may depend on implementation path.

---

## TC-028: Canonical text builder uses documented default options

**Category:**
Unit / Contract

**Priority:**
P0

**Source requirement:**
Canonical text is derived by `build_canonical_text`; default options exclude front matter, back matter, and footnotes, include chapter titles, and use fixed separators.

**Purpose:**
Verify exact builder output.

**Preconditions:**
Prepare fixture F022 book object.

**Input data:**
F022 `book`.

**Config / options:**
Use default builder options.

**Execution steps:**

1. Call `build_canonical_text(F022.book, options=None)`.
2. Compare returned string exactly.

**Expected result:**

```text
Chapter One

First chapter paragraph.

Second chapter paragraph.
```

**Expected assertions:**

* `assert text == expected_text`
* `assert F022.book is not mutated`

**Automation notes:**
Deep-copy F022 before calling builder and compare after call.

**Ambiguities:**
None.

---

## TC-029: Canonical text builder rejects invalid input as programmer error

**Category:**
Unit / Programmer error

**Priority:**
P0

**Source requirement:**
Invalid `book` or invalid `options` are programmer errors. Builder raises `TypeError` or `ValueError` and does not return extraction result.

**Purpose:**
Verify strict builder input policy.

**Preconditions:**
None.

**Input data:**

Case A:

```json
{
  "book": null,
  "options": null
}
```

Case B:

```json
{
  "book": {
    "title": "Invalid Book"
  },
  "options": null
}
```

Case C:

```json
{
  "book": "use F022 valid book",
  "options": {
    "unknown_option": true
  }
}
```

**Execution steps:**

1. Call builder for each case.
2. Capture exception.

**Expected result:**

* Case A raises `TypeError`;
* Case B raises `ValueError`;
* Case C raises `ValueError`;
* no `EpubContentExtractionResult` object is returned.

**Expected assertions:**

* `assert raises TypeError for null book`
* `assert raises ValueError for missing required book fields`
* `assert raises ValueError for unknown option field`

**Automation notes:**
Do not catch these errors inside extraction-result assertions.

**Ambiguities:**
None.

---

## TC-030: Repeated library runs are deterministic after volatile fields are normalized

**Category:**
Determinism / Regression

**Priority:**
P0

**Source requirement:**
For same input bytes, extractor version, config, and dependencies, output ordering, IDs, diagnostics order, and content must be deterministic. Timestamps and duration may differ.

**Purpose:**
Catch unstable ordering and nondeterministic IDs.

**Preconditions:**
Generate fixture F001 once and reuse exact file bytes.

**Input data:**
`tmp/epubs/minimal_valid.epub`.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run library extraction twice with the same file and config.
2. Normalize volatile fields:

   * `extraction.started_at`;
   * `extraction.finished_at`;
   * `extraction.duration_ms`.
3. Compare normalized results.

**Expected result:**

* both results succeed;
* normalized results are deeply equal;
* array ordering is stable;
* internal IDs are stable.

**Expected assertions:**

* `assert result1["status"] == result2["status"] == "succeeded"`
* `assert normalize(result1) == normalize(result2)`

**Automation notes:**
Do not normalize diagnostic order or chapter order; those must be stable.

**Ambiguities:**
None.

---

## TC-031: CLI `--pretty` and compact output parse to equivalent objects

**Category:**
CLI / Serialization

**Priority:**
P1

**Source requirement:**
`--pretty` affects JSON whitespace and indentation only. It must not change fields, values, ordering guarantees, diagnostics, counts, or semantics.

**Purpose:**
Verify serialization mode is presentation-only.

**Preconditions:**
Generate fixture F001.

**Input data:**
`tmp/epubs/minimal_valid.epub`.

**Config:**
No config.

**Execution steps:**

1. Run CLI without `--pretty`.
2. Run CLI with `--pretty`.
3. Parse both stdout values as JSON.
4. Normalize volatile timestamp/duration fields.
5. Compare parsed objects.

**Expected result:**

* both exit `0`;
* both parse as JSON;
* normalized objects are deeply equal.

**Expected assertions:**

* `assert compact_exit == 0`
* `assert pretty_exit == 0`
* `assert normalize(compact_json) == normalize(pretty_json)`

**Automation notes:**
Do not compare raw stdout strings.

**Ambiguities:**
None.

---

## TC-032: CLI invalid config file exits `4` and emits structured failed JSON

**Category:**
CLI / Invalid config

**Priority:**
P0

**Source requirement:**
CLI invalid config exits with code `4` and returns structured failed result when selected output channel is available.

**Purpose:**
Verify CLI config validation and exit mapping.

**Preconditions:**

* Generate fixture F001.
* Create config file `tmp/config/invalid_config.json`.

**Input file:**
`tmp/epubs/minimal_valid.epub`.

**Config file:**

`tmp/config/invalid_config.json`

```json
{
  "max_epub_size_bytes": "100MB"
}
```

**Execution steps:**

1. Run:

```bash
epub-content-extractor extract tmp/epubs/minimal_valid.epub --config tmp/config/invalid_config.json
```

2. Capture exit code and stdout.
3. Parse stdout as JSON.

**Expected result:**

* exit code `4`;
* stdout contains structured JSON failed result;
* `status = "failed"`;
* `error.code = "invalid_config"`;
* `book` absent;
* parsed JSON validates against schema.

**Expected assertions:**

* `assert exit_code == 4`
* `assert parsed["status"] == "failed"`
* `assert parsed["error"]["code"] == "invalid_config"`
* `assert "book" not in parsed`
* `assert parsed validates against schema`

**Automation notes:**
If `--output` is used and unwritable, exit code precedence changes to `3`; do not mix concerns in this test.

**Ambiguities:**
None.

---

## TC-033: CLI parser error exits `2` and emits no JSON result

**Category:**
CLI / Usage error

**Priority:**
P0

**Source requirement:**
CLI parser errors, missing required arguments, and invalid options print human-readable usage/error text to stderr and exit `2` without emitting a JSON result object.

**Purpose:**
Verify parser error is outside extraction-result contract.

**Preconditions:**
None.

**Input data:**
No EPUB file required.

**Execution steps:**

1. Run:

```bash
epub-content-extractor extract --unknown-option
```

2. Capture exit code, stdout, stderr.

**Expected result:**

* exit code `2`;
* stdout is empty or not a JSON extraction result;
* stderr contains human-readable usage/error text;
* no structured result JSON is emitted.

**Expected assertions:**

* `assert exit_code == 2`
* `assert stdout does not parse as EpubContentExtractionResult`
* `assert stderr is not empty`

**Automation notes:**
Do not validate stdout against result schema.

**Ambiguities:**
None.

---

## TC-034: CLI output write failure exits `3` and does not fall back to stdout

**Category:**
CLI / Filesystem / Regression

**Priority:**
P1

**Source requirement:**
If selected output destination cannot be written, CLI exits `3`. When `--output PATH` is requested, CLI must not fall back to stdout.

**Purpose:**
Verify output-channel failure precedence and no silent fallback.

**Preconditions:**

* Generate fixture F001.
* Create path `tmp/output_parent_missing/result.json` where parent directory does not exist, or create an unwritable directory on POSIX.

**Input data:**
`tmp/epubs/minimal_valid.epub`.

**Config:**
No config.

**Execution steps:**

1. Run:

```bash
epub-content-extractor extract tmp/epubs/minimal_valid.epub --output tmp/output_parent_missing/result.json
```

2. Capture exit code, stdout, stderr.
3. Check filesystem.

**Expected result:**

* exit code `3`;
* stdout does not contain fallback JSON result;
* output file is absent;
* stderr contains concise human-readable safe error.

**Expected assertions:**

* `assert exit_code == 3`
* `assert stdout == "" OR stdout does not parse as result JSON`
* `assert output file does not exist`
* `assert stderr is safe and concise`

**Automation notes:**
Missing parent directory is the most portable way to trigger this.

**Ambiguities:**
Exact stderr text is not stable API.

---

## TC-035: Debug field is absent by default

**Category:**
Debug / Contract / Privacy

**Priority:**
P0

**Source requirement:**
Debug mode is disabled by default. If `extraction.config.include_debug = false`, top-level `debug` must be absent.

**Purpose:**
Verify production output does not leak debug internals by default.

**Preconditions:**
Generate fixture F001.

**Input data:**
`tmp/epubs/minimal_valid.epub`.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run library extraction.
2. Inspect top-level fields.

**Expected result:**

* extraction succeeds;
* `extraction.config.include_debug = false`;
* top-level `debug` field absent;
* result validates against schema.

**Expected assertions:**

* `assert result["extraction"]["config"]["include_debug"] is False`
* `assert "debug" not in result`
* `assert result validates against schema`

**Automation notes:**
This is also schema-enforced; keep as production regression test.

**Ambiguities:**
None.

---

## TC-036: Debug enabled does not change production semantics

**Category:**
Debug / Determinism / Privacy

**Priority:**
P1

**Source requirement:**
`include_debug = true` may include top-level `debug`, but must not change extraction semantics, diagnostics, counts, or canonical text.

**Purpose:**
Verify debug mode is observational only.

**Preconditions:**
Generate fixture F001.

**Input data:**
`tmp/epubs/minimal_valid.epub`.

**Config A:**

```json
{
  "include_front_matter_in_canonical_text": false,
  "include_back_matter_in_canonical_text": false,
  "include_footnotes_in_canonical_text": false,
  "include_chapter_titles_in_canonical_text": true,
  "include_section_titles_in_canonical_text": false,
  "max_epub_size_bytes": 104857600,
  "max_html_document_size_bytes": 10485760,
  "max_text_block_chars": 100000,
  "pipeline_timeout_seconds": 120,
  "html_parse_timeout_seconds": 20,
  "max_archive_uncompressed_bytes": 524288000,
  "max_archive_entry_count": 10000,
  "max_archive_compression_ratio": 100,
  "max_toc_depth": 8,
  "max_diagnostic_count": 1000,
  "max_output_json_bytes": 524288000,
  "include_debug": false
}
```

**Config B:**

```json
{
  "include_front_matter_in_canonical_text": false,
  "include_back_matter_in_canonical_text": false,
  "include_footnotes_in_canonical_text": false,
  "include_chapter_titles_in_canonical_text": true,
  "include_section_titles_in_canonical_text": false,
  "max_epub_size_bytes": 104857600,
  "max_html_document_size_bytes": 10485760,
  "max_text_block_chars": 100000,
  "pipeline_timeout_seconds": 120,
  "html_parse_timeout_seconds": 20,
  "max_archive_uncompressed_bytes": 524288000,
  "max_archive_entry_count": 10000,
  "max_archive_compression_ratio": 100,
  "max_toc_depth": 8,
  "max_diagnostic_count": 1000,
  "max_output_json_bytes": 524288000,
  "include_debug": true
}
```

**Execution steps:**

1. Run extraction with Config A.
2. Run extraction with Config B.
3. Remove top-level `debug` from Config B result if present.
4. Normalize volatile fields.
5. Compare production fields.

**Expected result:**

* both runs succeed;
* Config B has `extraction.config.include_debug = true`;
* Config B may or may not include top-level `debug`;
* production fields other than `extraction.config.include_debug` and optional `debug` are semantically equal after volatile normalization;
* debug output, if present, does not contain absolute temp directory path or full raw HTML documents.

**Expected assertions:**

* `assert result_a["status"] == result_b["status"] == "succeeded"`
* `assert result_b["extraction"]["config"]["include_debug"] is True`
* `assert no absolute temp path appears in serialized result_b`
* `assert result_b validates against schema`

**Automation notes:**
Do not require debug field to exist because docs say it may be present but is not required.

**Ambiguities:**
Exact debug structure is implementation-specific.

---

## TC-037: Every emitted diagnostic code is documented and has correct severity

**Category:**
Diagnostics / Contract

**Priority:**
P0

**Source requirement:**
Every production diagnostic code must be documented. Each diagnostic code has exactly one valid severity in v2.2.

**Purpose:**
Catch undocumented diagnostic codes and severity drift.

**Preconditions:**
Run representative integration fixtures: F001 through F021 where applicable.

**Input data:**
All generated fixture outputs.

**Config:**
Each fixture’s own config.

**Execution steps:**

1. Collect diagnostics from all successful and failed structured results.
2. For each diagnostic, validate `code` and `severity` against matrix:

   * `metadata_missing_title`: `warning`
   * `metadata_missing_author`: `info`
   * `metadata_language_missing`: `info`
   * `metadata_language_conflicts_with_contract`: `warning`
   * `metadata_author_split_uncertain`: `warning`
   * `metadata_date_invalid`: `warning`
   * `table_of_contents_missing`: `info`
   * `toc_target_unresolved`: `warning`
   * `chapter_title_detected`: `info`
   * `chapter_title_uncertain`: `warning`
   * `chapter_type_uncertain`: `warning`
   * `front_matter_detected`: `info`
   * `back_matter_detected`: `info`
   * `copyright_section_detected`: `info`
   * `advertisement_section_detected`: `warning`
   * `publisher_notes_detected`: `info`
   * `table_of_contents_removed_from_canonical_text`: `info`
   * `footnote_detected`: `info`
   * `footnote_marker_removed`: `info`
   * `footnote_marker_unresolved`: `warning`
   * `footnote_owner_uncertain`: `warning`
   * `footnote_duplicate_marker`: `warning`
   * `page_number_removed`: `info`
   * `repeated_header_footer_removed`: `info`
   * `navigation_boilerplate_removed`: `info`
   * `artifact_removed`: `info`
   * `unicode_normalized`: `info`
   * `unicode_normalization_failed`: `warning`
   * `html_document_too_large_skipped`: `warning`
   * `html_document_parse_timeout_skipped`: `warning`
   * `text_block_too_large_split`: `warning`
   * `text_block_too_large_dropped`: `warning`
   * `empty_readable_content`: `error`
   * `quality_warning`: `warning`

**Expected result:**

* no undocumented diagnostic codes;
* every diagnostic severity matches matrix;
* every diagnostic has non-empty `message`;
* optional `entity_type`, if present, is one of documented values;
* result schema validation passes.

**Expected assertions:**

* `assert diagnostic.code in documented_codes`
* `assert diagnostic.severity == documented_severity[diagnostic.code]`
* `assert diagnostic.message is non-empty string`
* `assert no production result emits undocumented diagnostic code`

**Automation notes:**
This is a cross-fixture meta-test.

**Ambiguities:**
Not every documented diagnostic has a deterministic fixture in this guide.

---

## TC-038: Failed structured result contains error and no partial book

**Category:**
Contract / Negative

**Priority:**
P0

**Source requirement:**
When `status = "failed"`, `error` must exist, `book` must be absent, partial book output must not be included in normal mode.

**Purpose:**
Verify failure shape for all negative fixtures.

**Preconditions:**
Run negative fixtures F011, F012, F013, F014, F015, F016, F017, F020, F021.

**Input data:**
Each negative fixture.

**Config:**
Each fixture’s config.

**Execution steps:**

1. Run extraction for each fixture.
2. Validate common failed-result shape.

**Expected result:**

* `status = "failed"`;
* `error` exists;
* `error.recoverable = false`;
* `book` absent;
* `diagnostics` array exists;
* `extraction` exists;
* result validates against schema.

**Expected assertions:**

* `assert result["status"] == "failed"`
* `assert "error" in result`
* `assert result["error"]["recoverable"] is False`
* `assert "book" not in result`
* `assert isinstance(result["diagnostics"], list)`
* `assert "extraction" in result`
* `assert result validates against schema`

**Automation notes:**
Run this as parameterized test over all expected-failure fixtures.

**Ambiguities:**
None.

---

## TC-039: Production output does not leak absolute local paths

**Category:**
Security / Privacy / Regression

**Priority:**
P0

**Source requirement:**
Production diagnostics and metadata must not expose full local absolute input paths by default. `source_file.file_name`, when emitted, must be basename only.

**Purpose:**
Prevent privacy leaks.

**Preconditions:**
Generate fixtures in a temp directory with a unique path token such as `tmp/private_user_home_token/epubs/minimal_valid.epub`.

**Input data:**
Run fixture F001 from a directory whose absolute path includes unique token `private_user_home_token`.

**Config:**
Use fixture F000.

**Execution steps:**

1. Run extraction.
2. Serialize production result to JSON.
3. Search serialized JSON for absolute temp root and unique path token.

**Expected result:**

* extraction succeeds;
* serialized production output does not contain full absolute temp path;
* `metadata.source_file.file_name`, if present, equals basename only;
* no diagnostic `entity_id` contains absolute path;
* result validates against schema.

**Expected assertions:**

* `assert absolute_temp_root not in serialized_result`
* `assert "private_user_home_token" not in serialized_result except if it is part of basename intentionally`
* `assert "/" not in source_file.file_name and "\\" not in source_file.file_name`
* `assert result validates against schema`

**Automation notes:**
Make basename neutral, e.g. `minimal_valid.epub`, so the unique token appears only in directory path.

**Ambiguities:**
None.

---

## TC-040: Schema rejects invalid result shapes

**Category:**
Schema validation / Contract

**Priority:**
P0

**Source requirement:**
Official result schema must enforce success/failure branches, readable-content invariant, debug policy, required fields, enum values, and no additional properties.

**Purpose:**
Catch schema that is too permissive.

**Preconditions:**
Load official result schema.

**Input data:**

Case A: success result with both `book` and `error`.

```json
{
  "schema_version": "epub_content_extractor.v2.2",
  "status": "succeeded",
  "book": {
    "title": null,
    "subtitle": null,
    "language": "en",
    "authors": [],
    "contributors": [],
    "metadata": {
      "identifiers": [],
      "publisher": null,
      "published_at": null,
      "modified_at": null,
      "description": null,
      "rights": null,
      "subjects": [],
      "source_file": {
        "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "size_bytes": 1
      }
    },
    "front_matter": [],
    "chapters": [
      {
        "id": "chapter_001",
        "chapter_number": 1,
        "type": "chapter",
        "text": "Text.",
        "paragraphs": [
          {
            "text": "Text."
          }
        ],
        "footnotes": []
      }
    ],
    "back_matter": [],
    "footnotes": [],
    "table_of_contents": [],
    "assets": []
  },
  "error": {
    "code": "input_not_epub",
    "message": "Invalid.",
    "recoverable": false
  },
  "diagnostics": [],
  "extraction": {
    "extractor_version": "2.2.0",
    "started_at": "2026-05-08T10:00:00Z",
    "finished_at": "2026-05-08T10:00:01Z",
    "duration_ms": 1000,
    "config": {
      "include_front_matter_in_canonical_text": false,
      "include_back_matter_in_canonical_text": false,
      "include_footnotes_in_canonical_text": false,
      "include_chapter_titles_in_canonical_text": true,
      "include_section_titles_in_canonical_text": false,
      "max_epub_size_bytes": 104857600,
      "max_html_document_size_bytes": 10485760,
      "max_text_block_chars": 100000,
      "pipeline_timeout_seconds": 120,
      "html_parse_timeout_seconds": 20,
      "max_archive_uncompressed_bytes": 524288000,
      "max_archive_entry_count": 10000,
      "max_archive_compression_ratio": 100,
      "max_toc_depth": 8,
      "max_diagnostic_count": 1000,
      "max_output_json_bytes": 524288000,
      "include_debug": false
    },
    "summary": {
      "chapter_count": 1,
      "front_matter_section_count": 0,
      "back_matter_section_count": 0,
      "paragraph_count": 1,
      "footnote_count": 0,
      "total_text_chars": 5,
      "canonical_text_chars": 5,
      "removed_section_count": 0,
      "warning_count": 0,
      "error_count": 0
    }
  }
}
```

Case B: success result with error diagnostic.

```json
{
  "schema_version": "epub_content_extractor.v2.2",
  "status": "succeeded",
  "book": {
    "title": null,
    "subtitle": null,
    "language": "en",
    "authors": [],
    "contributors": [],
    "metadata": {
      "identifiers": [],
      "publisher": null,
      "published_at": null,
      "modified_at": null,
      "description": null,
      "rights": null,
      "subjects": [],
      "source_file": {
        "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "size_bytes": 1
      }
    },
    "front_matter": [],
    "chapters": [
      {
        "id": "chapter_001",
        "chapter_number": 1,
        "type": "chapter",
        "text": "Text.",
        "paragraphs": [
          {
            "text": "Text."
          }
        ],
        "footnotes": []
      }
    ],
    "back_matter": [],
    "footnotes": [],
    "table_of_contents": [],
    "assets": []
  },
  "diagnostics": [
    {
      "code": "empty_readable_content",
      "severity": "error",
      "message": "No readable content."
    }
  ],
  "extraction": {
    "extractor_version": "2.2.0",
    "started_at": "2026-05-08T10:00:00Z",
    "finished_at": "2026-05-08T10:00:01Z",
    "duration_ms": 1000,
    "config": {
      "include_front_matter_in_canonical_text": false,
      "include_back_matter_in_canonical_text": false,
      "include_footnotes_in_canonical_text": false,
      "include_chapter_titles_in_canonical_text": true,
      "include_section_titles_in_canonical_text": false,
      "max_epub_size_bytes": 104857600,
      "max_html_document_size_bytes": 10485760,
      "max_text_block_chars": 100000,
      "pipeline_timeout_seconds": 120,
      "html_parse_timeout_seconds": 20,
      "max_archive_uncompressed_bytes": 524288000,
      "max_archive_entry_count": 10000,
      "max_archive_compression_ratio": 100,
      "max_toc_depth": 8,
      "max_diagnostic_count": 1000,
      "max_output_json_bytes": 524288000,
      "include_debug": false
    },
    "summary": {
      "chapter_count": 1,
      "front_matter_section_count": 0,
      "back_matter_section_count": 0,
      "paragraph_count": 1,
      "footnote_count": 0,
      "total_text_chars": 5,
      "canonical_text_chars": 5,
      "removed_section_count": 0,
      "warning_count": 0,
      "error_count": 1
    }
  }
}
```

Case C: result contains top-level debug while `include_debug = false`.

```json
{
  "schema_version": "epub_content_extractor.v2.2",
  "status": "failed",
  "error": {
    "code": "input_not_epub",
    "message": "Invalid.",
    "recoverable": false
  },
  "diagnostics": [],
  "extraction": {
    "extractor_version": "2.2.0",
    "started_at": "2026-05-08T10:00:00Z",
    "finished_at": "2026-05-08T10:00:00Z",
    "duration_ms": 0,
    "config": {
      "include_front_matter_in_canonical_text": false,
      "include_back_matter_in_canonical_text": false,
      "include_footnotes_in_canonical_text": false,
      "include_chapter_titles_in_canonical_text": true,
      "include_section_titles_in_canonical_text": false,
      "max_epub_size_bytes": 104857600,
      "max_html_document_size_bytes": 10485760,
      "max_text_block_chars": 100000,
      "pipeline_timeout_seconds": 120,
      "html_parse_timeout_seconds": 20,
      "max_archive_uncompressed_bytes": 524288000,
      "max_archive_entry_count": 10000,
      "max_archive_compression_ratio": 100,
      "max_toc_depth": 8,
      "max_diagnostic_count": 1000,
      "max_output_json_bytes": 524288000,
      "include_debug": false
    },
    "summary": {
      "chapter_count": 0,
      "front_matter_section_count": 0,
      "back_matter_section_count": 0,
      "paragraph_count": 0,
      "footnote_count": 0,
      "total_text_chars": 0,
      "canonical_text_chars": 0,
      "removed_section_count": 0,
      "warning_count": 0,
      "error_count": 1
    }
  },
  "debug": {
    "parser": {}
  }
}
```

**Execution steps:**

1. Validate each case against official result schema.
2. Confirm each case is rejected.

**Expected result:**

* Case A rejected because success cannot contain `error`;
* Case B rejected because successful result cannot contain error diagnostics;
* Case C rejected because `debug` is forbidden when `include_debug = false`.

**Expected assertions:**

* `assert schema_validation(case_a) fails`
* `assert schema_validation(case_b) fails`
* `assert schema_validation(case_c) fails`

**Automation notes:**
These are schema-only tests and do not call the extractor.

**Ambiguities:**
None.

---

## 7. Negative and Edge Case Coverage

| Area                          | Covered by | Expected behavior                         |
| ----------------------------- | ---------- | ----------------------------------------- |
| Missing file                  | TC-010     | `input_file_not_found`                    |
| Directory input               | TC-011     | `input_not_file`                          |
| Programmer error path         | TC-012     | raises `TypeError`                        |
| Plain non-ZIP `.epub`         | TC-013     | `input_not_epub`                          |
| Valid ZIP but no EPUB package | TC-014     | `epub_manifest_unreadable`                |
| Archive path traversal        | TC-015     | `epub_archive_security_violation`         |
| Excessive archive entries     | TC-016     | `epub_archive_security_violation`         |
| Excessive compression ratio   | TC-017     | `epub_archive_security_violation`         |
| Input file too large          | TC-018     | `epub_file_too_large`                     |
| Invalid config unknown field  | TC-006     | `invalid_config` before path validation   |
| Invalid config wrong type     | TC-007     | `invalid_config`                          |
| Config above maximum          | TC-009     | `invalid_config`                          |
| Missing metadata              | TC-019     | success + diagnostics                     |
| Non-English metadata language | TC-020     | success + warning, output language `"en"` |
| Invalid date                  | TC-021     | date `null` + warning                     |
| Duplicate metadata            | TC-022     | deterministic deduplication               |
| Ambiguous author split        | TC-023     | no unsafe split                           |
| Duplicate footnote markers    | TC-025     | warning / no silent removal               |
| Oversized HTML partial skip   | TC-026     | success + warning                         |
| All content skipped           | TC-027     | `no_readable_content`                     |
| CLI parser error              | TC-033     | exit `2`, no JSON result                  |
| CLI output write failure      | TC-034     | exit `3`, no stdout fallback              |
| Debug disabled                | TC-035     | no `debug` field                          |
| Path privacy                  | TC-039     | no absolute local paths                   |

Missing deterministic coverage due to documentation gaps:

* `html_document_parse_timeout_skipped`;
* `pipeline_timeout`;
* `unicode_normalization_failed`;
* `text_block_too_large_dropped`;
* exact `chapter_title_uncertain`;
* exact `chapter_type_uncertain`.

These should be added either after implementation exposes deterministic test seams or after documentation defines exact trigger fixtures.

---

## 8. Contract and Schema Validation Tests

### 8.1 Result schema validation

Every integration test that receives a structured result must validate it against:

```text
schema/epub_content_extractor.v2.2.schema.json
```

Required assertions:

* top-level object has no unknown fields;
* `schema_version = "epub_content_extractor.v2.2"`;
* success result has `book` and no `error`;
* failed result has `error` and no `book`;
* `diagnostics` always exists;
* `extraction` always exists;
* `debug` absent when `extraction.config.include_debug = false`;
* success result has at least one readable chapter/front/back section;
* success result has no diagnostic with `severity = "error"`.

### 8.2 Config schema validation

Config tests must validate:

* `{}` is accepted and defaults are applied by application code;
* `$schema` URI is accepted but omitted from output config;
* unknown fields are rejected;
* string numeric values are rejected;
* floats are rejected where integer is required;
* values below minimum are rejected;
* values above maximum are rejected;
* maximum values are accepted;
* `config_version` is rejected in v2.2 because not allowed by schema.

### 8.3 Diagnostic registry validation

Registry-driven tests MUST load `schema/epub_content_extractor_diagnostic_registry.v2.2.json` and `schema/epub_content_extractor_error_registry.v2.2.json`.

For every production result:

* diagnostic code must be one of documented v2.2 codes;
* severity must match documented matrix;
* message must be non-empty string;
* optional `entity_type` must be one of:

  * `book`;
  * `chapter`;
  * `section`;
  * `footnote`;
  * `toc_item`;
  * `asset`;
  * `config`;
  * `archive_entry`;
  * `input_file`;
* optional `entity_id` must not expose absolute local path;
* optional `field` must be non-empty string.


### 8.3.1 Diagnostic coverage matrix

Every diagnostic code MUST have an explicit coverage status in `schema/epub_content_extractor_diagnostic_registry.v2.2.json`. The testing guide treats the registry as the machine-readable source of truth and this table as the human-readable coverage plan.

Allowed coverage statuses:

```text
integration_fixture
unit_fixture
fault_injection
schema_only
reserved_not_emitted_by_default
requires_contract_decision
```

For release-candidate v2.2 registries, `requires_contract_decision` MUST NOT appear. It is a draft-only status used to block release until the code is either fixture-backed, fault-injection-backed, schema-only, or explicitly `reserved_not_emitted_by_default`.

A code marked `reserved_not_emitted_by_default` may remain in the result schema for compatibility, but production code MUST NOT emit it in v2.2. Tests MUST assert that default production fixtures do not emit reserved diagnostic codes.

| Diagnostic code | Coverage status | Required test or decision |
|---|---|---|
| `metadata_missing_title` | `integration_fixture` | TC-019 |
| `metadata_missing_author` | `integration_fixture` | TC-019 |
| `metadata_language_missing` | `integration_fixture` | TC-019 |
| `metadata_language_conflicts_with_contract` | `integration_fixture` | TC-020 |
| `metadata_author_split_uncertain` | `integration_fixture` | TC-023 |
| `metadata_date_invalid` | `integration_fixture` | TC-021 |
| `table_of_contents_missing` | `integration_fixture` | TC-019 or dedicated TOC-missing fixture |
| `toc_target_unresolved` | `integration_fixture` | TC-P1-DIAG-004 |
| `chapter_title_detected` | `integration_fixture` | TC-001 or TC-024 |
| `chapter_title_uncertain` | `reserved_not_emitted_by_default` | Schema-reserved in v2.2; production code MUST NOT emit by default |
| `chapter_type_uncertain` | `reserved_not_emitted_by_default` | Schema-reserved in v2.2; production code MUST NOT emit by default |
| `front_matter_detected` | `integration_fixture` | TC-024 |
| `back_matter_detected` | `integration_fixture` | TC-024 |
| `copyright_section_detected` | `integration_fixture` | TC-P1-DIAG-005 |
| `advertisement_section_detected` | `integration_fixture` | TC-P1-DIAG-006 |
| `publisher_notes_detected` | `integration_fixture` | TC-P1-DIAG-007 |
| `table_of_contents_removed_from_canonical_text` | `integration_fixture` | TC-P1-DIAG-008 |
| `footnote_detected` | `integration_fixture` | TC-024 |
| `footnote_marker_removed` | `integration_fixture` | TC-024 if marker is resolved |
| `footnote_marker_unresolved` | `integration_fixture` | TC-025 |
| `footnote_owner_uncertain` | `integration_fixture` | TC-P1-DIAG-009 |
| `footnote_duplicate_marker` | `integration_fixture` | TC-025 |
| `page_number_removed` | `integration_fixture` | TC-P1-DIAG-010 |
| `repeated_header_footer_removed` | `integration_fixture` | TC-P1-DIAG-011 |
| `navigation_boilerplate_removed` | `integration_fixture` | TC-P1-DIAG-012 |
| `artifact_removed` | `integration_fixture` | TC-P1-DIAG-013 |
| `unicode_normalized` | `integration_fixture` | TC-P1-DIAG-014 |
| `unicode_normalization_failed` | `fault_injection` | TC-P1-DIAG-015 or mark reserved |
| `html_document_too_large_skipped` | `integration_fixture` | TC-026 |
| `html_document_parse_timeout_skipped` | `fault_injection` | TC-P1-TIMEOUT-001 |
| `text_block_too_large_split` | `integration_fixture` | TC-P1-LIM-004 |
| `text_block_too_large_dropped` | `reserved_not_emitted_by_default` | Schema-reserved in v2.2; production code MUST NOT emit by default |
| `empty_readable_content` | `integration_fixture` | TC-027 when content analysis reached |
| `quality_warning` | `integration_fixture` | TC-P1-LIM-005 |

### 8.4 Error code validation

For every failed result:

* `error.code` must be one of:

  * `invalid_config`;
  * `input_file_not_found`;
  * `input_not_file`;
  * `input_not_epub`;
  * `epub_file_too_large`;
  * `epub_open_failed`;
  * `epub_manifest_unreadable`;
  * `epub_archive_security_violation`;
  * `no_readable_content`;
  * `pipeline_timeout`;
  * `output_write_failed`;
  * `internal_error`;
* `error.recoverable = false`;
* `error.message` is non-empty string;
* `book` is absent.

### 8.5 CLI exit-code validation

| Scenario               | Expected exit code | JSON result                        |
| ---------------------- | -----------------: | ---------------------------------- |
| Successful extraction  |                `0` | yes                                |
| Failed extraction      |                `1` | yes                                |
| CLI usage/parser error |                `2` | no                                 |
| Output write failure   |                `3` | no fallback JSON                   |
| Invalid config         |                `4` | yes if output channel available    |
| Internal error         |               `99` | yes only if constructable/writable |

`output_write_failed` is not expected from the canonical `extract_epub_content()` library API. In the canonical CLI, output write failure usually prevents JSON serialization to the selected channel, so tests for exit `3` MUST assert no fallback JSON is written to stdout unless a future contract explicitly defines a secondary diagnostic channel.


### 8.6 P0/P1 contract tests required for 9+/10 readiness

The following test cases are mandatory before the package can claim 9+/10 automated-test-generation readiness. They extend the existing TC-001..TC-040 suite and are intentionally written as stable contract IDs.

| Test ID | Priority | Area | Requirement covered | Expected behavior |
|---|---|---|---|---|
| `TC-P0-SCHEMA-001` | P0 | Schema | Canonical schema files exist | Versioned schema files load from `schema/` and validate as Draft 2020-12 schemas |
| `TC-P0-SCHEMA-002` | P0 | Schema | Schema IDs match v2.2 | `$id` values match documented v2.2 URIs |
| `TC-P1-API-001` | P1 | API | Builder partial options | `build_canonical_text()` accepts partial boolean mappings and does not mutate inputs |
| `TC-P1-API-002` | P1 | API | Builder rejects separators | Separator option keys raise `ValueError` |
| `TC-P1-DIAG-001` | P1 | Diagnostics | Diagnostic registry matches result schema | Code set and severity map are identical |
| `TC-P1-DIAG-002` | P1 | Errors | Error registry matches result schema and CLI table | Error code set, recoverable flag, and exit mappings agree |
| `TC-P1-DIAG-003` | P1 | Diagnostics | Every registry code has coverage status | No undocumented empty coverage decisions |
| `TC-P1-FIX-001` | P1 | Fixtures | Generator specs are deterministic | Repeated generation produces same logical fixture manifest and same normalized extraction result |
| `TC-P1-FIX-002` | P1 | Fixtures | Golden outputs validate after normalization | Key `expected.normalized.json` files match public output after approved normalization only |
| `TC-P1-TIMEOUT-001` | P1 | Timeout | HTML parse timeout | Forced parser timeout emits `html_document_parse_timeout_skipped` without wall-clock sleep |
| `TC-P1-TIMEOUT-002` | P1 | Timeout | Whole-pipeline timeout | Forced pipeline timeout returns `pipeline_timeout` failed result |
| `TC-P1-SEC-001` | P1 | Security | Absolute ZIP entry path | `epub_archive_security_violation` |
| `TC-P1-SEC-002` | P1 | Security | Windows drive-letter ZIP path | `epub_archive_security_violation` |
| `TC-P1-SEC-003` | P1 | Security | UNC ZIP path | `epub_archive_security_violation` |
| `TC-P1-SEC-004` | P1 | Security | Backslash traversal ZIP path | `epub_archive_security_violation` |
| `TC-P1-SEC-005` | P1 | Security | Symlink-like ZIP entry | `epub_archive_security_violation` before OPF parsing |
| `TC-P1-SEC-006` | P1 | Security | Encrypted ZIP entry | `epub_archive_security_violation` or external-tool fixture requirement |
| `TC-P1-SEC-007` | P1 | Security | XML external entity is not resolved | No network/file fetch and no leaked external content |
| `TC-P1-SEC-008` | P1 | Security | External image/CSS URL is not fetched | No network request and no fetched content |
| `TC-P1-CFG-001` | P1 | Config | `config_version` rejected | `invalid_config`; CLI exit `4` |
| `TC-P1-CFG-002` | P1 | Config | Numeric floats rejected | `invalid_config` |
| `TC-P1-CFG-003` | P1 | Config | Numeric below-minimum values rejected | `invalid_config` |
| `TC-P1-CFG-004` | P1 | Config | `$schema` absolute URI assertion | `invalid_config` for non-URI `$schema` |
| `TC-P1-CLI-001` | P1 | CLI | `--version` | Exit `0` without input/config validation |
| `TC-P1-CLI-002` | P1 | CLI | `--help` | Exit `0` without input/config validation |
| `TC-P1-CLI-003` | P1 | CLI | `--config -` | Reads config from stdin and applies it |
| `TC-P1-CLI-004` | P1 | CLI | `--output -` | Writes result JSON to stdout |
| `TC-P1-CLI-005` | P1 | CLI | Atomic overwrite | Existing output replaced atomically; no temp files remain |
| `TC-P1-CLI-006` | P1 | CLI | Invalid config plus unwritable output | Exit `3` when selected output channel is unavailable |

---

## 8.7 Additional P1 test contracts

#### TC-P1-DIAG-016: Registry codes are unique by `code`

**Purpose:** Ensure diagnostic and error registries cannot contain duplicate code keys with different fields.  
**Input fixture:** Load both registry JSON files:

```text
schema/epub_content_extractor_diagnostic_registry.v2.2.json
schema/epub_content_extractor_error_registry.v2.2.json
```

**Steps:**

1. Build `Counter(entry["code"] for entry in diagnostics)`.
2. Build `Counter(entry["code"] for entry in errors)`.
3. Compare registry code sets against the result schema diagnostic/error enum sets.
4. Assert no release-candidate registry entry has `coverage_status = "requires_contract_decision"`.
5. Assert no production extraction fixture emits a diagnostic with `coverage_status = "reserved_not_emitted_by_default"`.

**Expected result:** every diagnostic and error code appears exactly once in its registry, and registry code sets match the result schema.  
**Assertions:** no duplicate diagnostic codes; no duplicate error codes; no missing/extra codes; no draft-only status in release-candidate registry.  
**Pass/Fail criteria:** fail on duplicate keys, schema/registry drift, or release-blocking coverage status.

#### TC-P1-CFG-004: `$schema` must be an absolute URI

**Purpose:** Ensure config validation treats `$schema` as tooling-only but still validates its type and URI shape consistently.  
**Config:**

```json
{ "$schema": "not a uri" }
```

**Expected behavior:** `invalid_config`.  
**Required assertions:** production validation and contract tests use the same URI assertion behavior. If the JSON Schema validator treats `format: "uri"` as annotation by default, the validator MUST be configured with format assertions or the schema pattern MUST reject the value.

#### TC-P1-GOLDEN-001: Golden acceptance manifest validates against schema

**Purpose:** Ensure the minimum golden-output acceptance manifest is machine-checkable.  
**Input fixture:**

```text
docs/testing/epub_content_extractor_golden_acceptance_manifest.v2.2.json
schema/epub_content_extractor_golden_acceptance_manifest.v2.2.schema.json
```

**Steps:**

1. Load the manifest JSON.
2. Load the manifest schema.
3. Validate the manifest against the schema.
4. Assert `minimum_required_goldens` contains unique paths matching `tests/fixtures/epub_content_extractor/**/expected.normalized.json`.

**Expected result:** manifest is valid and contains no duplicate or malformed golden paths.  
**Pass/Fail criteria:** fail if the schema is missing, the manifest is invalid, or any listed path is malformed.

#### TC-P1-GOLDEN-002: Minimum golden paths are complete before release

**Purpose:** Prevent a release from claiming final golden-snapshot readiness without real expected outputs.  
**Input fixture:** `docs/testing/epub_content_extractor_golden_acceptance_manifest.v2.2.json`.

**Steps:**

1. Load the manifest.
2. If `status = "pending_until_real_goldens_committed"`, mark the golden acceptance suite as incomplete and fail the release-readiness gate.
3. If `status = "complete"`, assert every listed path exists.
4. For each listed file, assert it is valid JSON.
5. Validate each listed expected output against `schema/epub_content_extractor.v2.2.schema.json` after applying the documented snapshot-normalization policy.

**Expected result:** release-readiness passes only when the manifest is `complete` and every minimum golden output exists and validates.  
**Pass/Fail criteria:** fail on missing paths, placeholder files, invalid JSON, schema-invalid expected outputs, or `pending_until_real_goldens_committed` during a release-readiness run.


## 9. Regression Tests

### R-001: Invalid config must not be masked by missing input

Covered by TC-006.

Regression risk:

* implementation validates path before config and returns `input_file_not_found`.

Expected protection:

* invalid config always wins over path validation.

### R-002: Valid ZIP must not be accepted as EPUB

Covered by TC-014.

Regression risk:

* extractor treats any readable ZIP as success or empty book.

Expected protection:

* returns `epub_manifest_unreadable`.

### R-003: Archive security must precede OPF parsing

Covered by TC-015.

Regression risk:

* implementation tries to locate/parse OPF before rejecting unsafe entries.

Expected protection:

* path traversal returns `epub_archive_security_violation`, not `epub_manifest_unreadable`.

### R-004: Success with no readable content must be impossible

Covered by TC-027 and TC-040.

Regression risk:

* extractor returns `status = "succeeded"` with empty chapters/sections.

Expected protection:

* runtime emits `no_readable_content`;
* schema rejects success result with no readable content.

### R-005: Debug leakage in production output

Covered by TC-035 and TC-039.

Regression risk:

* raw HTML, absolute path, debug scoring, or source maps leak into normal output.

Expected protection:

* no top-level `debug` unless enabled;
* no absolute temp root path in production result.

### R-006: Diagnostic severity drift

Covered by TC-037.

Regression risk:

* implementation emits `metadata_language_missing` as warning instead of info, or introduces undocumented code.

Expected protection:

* registry test fails.

### R-007: Non-deterministic IDs/order

Covered by TC-030.

Regression risk:

* IDs depend on dict iteration, filesystem order, timestamps, or random values.

Expected protection:

* repeated runs are equal after only volatile timestamp/duration normalization.

### R-008: CLI `--pretty` changes semantics

Covered by TC-031.

Regression risk:

* pretty mode uses a different serialization/result path.

Expected protection:

* parsed compact and pretty results match semantically.

### R-009: Raw invalid config leaked in failed output

Covered by TC-007.

Regression risk:

* production failed result includes `"100MB"` or unknown raw config fields.

Expected protection:

* invalid config output uses default snapshot and excludes raw invalid values.

### R-010: Unsafe broad author splitting

Covered by TC-023.

Regression risk:

* comma-separated creator string is split into invalid person objects.

Expected protection:

* no author named only `"editor"` and no split solely by comma.

---

## 10. Recommendations for Test Automation

1. Generate all valid EPUB test fixtures dynamically with `ebooklib`.

   Required generator behavior:

   * create file under test temp directory;
   * write deterministic metadata;
   * write deterministic XHTML strings;
   * write deterministic spine/TOC;
   * avoid current timestamps in EPUB metadata unless intentionally testing date normalization;
   * return actual file path, file size, and SHA-256 bytes.

2. Generate invalid/security EPUB fixtures with `zipfile`.

   Required cases:

   * plain ZIP without EPUB package;
   * traversal entries;
   * absolute internal paths;
   * excessive entries;
   * excessive compression ratio;
   * malformed or missing OPF/container files.

3. Use a common result-normalization helper for deterministic comparisons.

   Normalize only:

   * `extraction.started_at`;
   * `extraction.finished_at`;
   * `extraction.duration_ms`.

   Do not normalize:

   * chapter order;
   * paragraph order;
   * diagnostics order;
   * internal IDs;
   * metadata ordering.

4. Validate every structured result against official schema.

   This must happen in all integration tests, including expected failures.

5. Keep tests black-box at public boundaries.

   Prefer:

   * `extract_epub_content`;
   * `build_canonical_text`;
   * CLI process invocation.

   Avoid asserting internal parser classes, scoring values, raw blocks, or debug internals.

6. Use invariant-based assertions for heuristic extraction areas.

   For chapters, sections, TOC, and footnotes, assert contract invariants unless docs define exact behavior.

7. Separate CLI tests from library tests.

   CLI tests should assert:

   * exit code;
   * stdout/stderr channel behavior;
   * JSON parseability;
   * no fallback behavior;
   * output file behavior.

8. Add fault-injection seams for timeout tests.

   To test `pipeline_timeout` and `html_document_parse_timeout_skipped` deterministically, the implementation should allow test injection of clock/timer/parser boundaries. Without such seams, wall-clock timeout tests should not be P0.

9. Avoid external book fixtures for contract tests.

   Real EPUBs such as Gutenberg books may be useful as smoke tests, but P0 contract tests should use generated minimal fixtures so failures are easy to diagnose.

10. Add a generated-fixture manifest in the test helper output.

The helper should record, for debugging only:

* generated EPUB path;
* generator name and version;
* logical fixture ID;
* SHA-256;
* file size;
* list of intended internal files.

This helper manifest is not part of the module output contract.

---

## Test Case Self-Containment Checklist

| Check                                                                     | Pass/Fail | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Every test case has complete input data                                   | Pass      | Each test references a fixture that contains exact generated EPUB metadata, XHTML content, config, or invalid ZIP entries.                                                                                                                                                                                                                                                                                                                                          |
| Every test case has expected result                                       | Pass      | Each detailed test includes exact status/error/diagnostic/schema expectations or explicit invariant-based expectations.                                                                                                                                                                                                                                                                                                                                             |
| Every test case can be converted into automated test without reading docs | Pass      | Required inputs, configs, execution steps, and assertions are included in this guide.                                                                                                                                                                                                                                                                                                                                                                               |
| All schema contracts are covered                                          | Pass      | Result schema, config schema, debug policy, success/failure branch, readable-content invariant, and diagnostic severity matrix are covered.                                                                                                                                                                                                                                                                                                                         |
| Every diagnostic code has an explicit coverage status                     | Pass      | Production-emittable diagnostics map to integration, unit, schema-only, or fault-injection coverage. Schema-reserved diagnostics such as `chapter_title_uncertain`, `chapter_type_uncertain`, and `text_block_too_large_dropped` are marked `reserved_not_emitted_by_default` and MUST NOT be emitted by v2.2 production fixtures. |
| Negative cases are specific and executable                                | Pass      | Missing files, directories, non-ZIP input, ZIP-not-EPUB, archive traversal, entry count, compression ratio, invalid config, and file-size limit are executable.                                                                                                                                                                                                                                                                                                     |
| Ambiguities are explicitly marked                                         | Pass      | Known heuristic and timeout-related gaps are listed in Section 2 and in relevant test cases.                                                                                                                                                                                                                                                                                                                                                                        |


### TC-P1-SCHEMA-DRIFT-EMBEDDED-001: Embedded config schema excerpt matches canonical `$schema` constraints

**Purpose:** Prevent Markdown schema snippets from drifting from canonical schema artifacts.

**Input fixture:**

```text
docs/architecture/epub_content_extractor_architecture.md
schema/epub_content_extractor_config.v2.2.schema.json
```

**Steps:**

1. Load the canonical config schema.
2. Inspect the architecture Markdown Section 4.1.1.
3. If a full inline config schema block is present, assert that the `$schema` property includes both `format: "uri"` and `pattern: "^[A-Za-z][A-Za-z0-9+.-]*:"`.
4. If the inline schema block is replaced by a reference-only section in the future, assert that the section names `schema/epub_content_extractor_config.v2.2.schema.json` as the normative source.

**Expected result:** The Markdown architecture does not imply weaker `$schema` validation than the canonical schema file.

**Pass/Fail criteria:** Fail if the embedded Markdown copy omits canonical `$schema` constraints or describes `$schema` as a non-absolute/non-URI value.


### Final v2.2 minimum golden set

The seven `expected.normalized.json` files listed by `docs/testing/epub_content_extractor_golden_acceptance_manifest.v2.2.json` are included as manually approved contract examples. They are not placeholders. They use schema-preserving normalized timestamps and MUST be treated as normative v2.2 snapshot baselines until an accepted implementation deliberately updates them through review.
