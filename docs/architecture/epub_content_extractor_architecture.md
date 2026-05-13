# epub_content_extractor — Architecture and Contract v3.0

## 1. Purpose

`epub_content_extractor` converts `.epub` files into a structured, self-contained book object.

The module does **not** return plain text as the primary output. The official output is a JSON-serializable structured object that describes the extracted book:

- title and subtitle;
- fixed English language contract;
- authors and contributors;
- EPUB metadata;
- front matter;
- chapters / acts / scenes / parts;
- back matter;
- front/back matter paragraphs;
- footnotes and endnotes;
- table of contents;
- lightweight asset metadata;
- diagnostics;
- extraction summary.

The output schema must describe the resulting document, not the internal extraction pipeline.

The extractor is intended for downstream English NLP pipelines. It must remain independently usable as a Python library and as a CLI tool.

---

## 2. Scope

### 2.1 Supported interfaces

The module is available only as:

1. Python library;
2. CLI command.

The module does **not** define or own:

- HTTP API;
- authentication;
- authorization;
- roles or permissions;
- database integration;
- queue integration;
- external object/file storage integration.

Any HTTP API, background job system, database persistence, file storage, or permission model must be implemented by a higher-level service that calls this module.

### 2.2 Non-goals

The extractor does not attempt to:

- render EPUB visually;
- preserve CSS layout;
- preserve page layout;
- OCR images;
- extract binary image data;
- extract fonts, stylesheets, or scripts as output content;
- infer missing book content from incomplete EPUB files;
- support non-English books;
- guarantee perfect semantic classification for every publisher-specific EPUB layout.


### 2.3 Documentation precedence

For `epub_content_extractor`, normative requirements are resolved in this order:

1. JSON Schema and registry artifacts under `schema/`;
2. this module-specific architecture and contract document;
3. the module-specific testing guide;
4. shared project guidelines under `docs/guidelines/`.

If a shared guideline conflicts with this module-specific contract, this module-specific contract wins.

Examples:

- The module-specific CLI exit-code table overrides generic CLI guideline exit-code categories.
- The module-specific stdout/stderr contract overrides generic logging recommendations.
- The module-specific debug redaction policy overrides generic “full tracing” wording.
- No environment-variable config source exists unless this module-specific contract defines it.

---

## 3. Language contract

`epub_content_extractor` is an English-only extractor.

### 3.1 Fixed output language

The output book language is always:

```json
"language": "en"
```

The field is required and must not be `null`.

```typescript
type EpubBookLanguage = "en";
```

### 3.2 No language detection

The extractor must not run language detection by default.

Rules:

- `book.language` is always `"en"`;
- EPUB metadata may be read for diagnostics only;
- EPUB metadata must not override `book.language`;
- if EPUB metadata language is missing, extraction still succeeds and emits `metadata_language_missing` with severity `info`;
- if EPUB metadata language is present and is not English-like, extraction still produces `book.language = "en"` and emits diagnostic `metadata_language_conflicts_with_contract` with severity `warning`;
- actual non-English content quality is outside the v3.0 contract;
- if an EPUB contains non-English content but metadata language is missing, extraction still follows the normal English-only contract and must not emit a content-language diagnostic because content language detection is not performed;
- if actual non-English content is extracted, no diagnostic is required unless a future optional language detector is explicitly enabled outside the v3.0 default contract.

Rationale: this extractor is part of an English-learning pipeline. The language is a product-level invariant, not a value inferred from the EPUB.

Note: `book.language = "en"` does not certify that every extracted sentence is English; it is the fixed product contract value.

### 3.3 English-like metadata language criteria

Metadata language is considered English-like only after deterministic normalization:

1. trim leading/trailing whitespace;
2. convert `_` to `-`;
3. lowercase ASCII letters;
4. remove surrounding quotes if present.

Accepted English-like values:

- exactly `en`;
- BCP-47 values whose primary language subtag is `en`, for example `en-us`, `en-gb`, `en-ca`, `en-latn-us`;
- ISO-639-2/T legacy aliases `eng` and `english`.

Rejected values include non-English primary subtags such as `fr`, `de`, `ru`, `es`, `pt-br`, `ang`, `enm`, and mixed lists where no English-like value is present.

If metadata contains multiple language values and at least one value is English-like, no conflict diagnostic is required. Non-English additional values may emit `metadata_language_conflicts_with_contract` only when they indicate that the EPUB is primarily non-English.

---

## 4. Public entry points

### 4.1 Python library function

The canonical public library entry point is:

```python
from epub_content_extractor import extract_epub_content

result = extract_epub_content(
    input_path: str | Path,
    config: EpubContentExtractorConfig | None = None,
) -> EpubContentExtractionResult
```

Contract:

- `input_path` must point to a local readable file. The `.epub` filename extension is advisory; EPUB validity is determined from file contents and EPUB package/security checks.
- `config` is optional.
- The function must return an `EpubContentExtractionResult` object for expected extraction outcomes.
- The function must not raise exceptions for normal domain failures such as invalid config, invalid EPUB, unreadable EPUB, empty readable content, or parse failure.
- Invalid config in library mode is an expected failed extraction result: `status = "failed"`, `error.code = "invalid_config"`, `error.recoverable = false`.
- Normal domain failures must be represented as `status: "failed"` with a structured `error` object.
- Exceptions are reserved for unexpected implementation defects that prevent a structured result from being constructed.

### 4.1.1 `EpubContentExtractorConfig` JSON Schema

The official config schema is `schema/epub_content_extractor_config.v3.0.schema.json`.

This Markdown schema block is an explanatory copy of the canonical file. It MUST NOT be maintained as an independent schema source. Release validation MUST fail if this inline copy implies weaker validation than `schema/epub_content_extractor_config.v3.0.schema.json`, especially for the tooling-only `$schema` URI constraints.


The schema is closed: unknown config fields are invalid, except for the tooling-only input field `$schema`, which is explicitly allowed and ignored semantically.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.deszo.local/epub_content_extractor_config.v3.0.schema.json",
  "title": "EpubContentExtractorConfig",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "$schema": {
      "type": "string",
      "format": "uri",
      "description": "Optional tooling-only absolute schema URI accepted in input config. Ignored during semantic config processing and omitted from extraction.config.",
      "pattern": "^[A-Za-z][A-Za-z0-9+.-]*:"
    },
    "include_front_matter_in_canonical_text": {
      "type": "boolean",
      "default": false
    },
    "include_back_matter_in_canonical_text": {
      "type": "boolean",
      "default": false
    },
    "include_footnotes_in_canonical_text": {
      "type": "boolean",
      "default": false
    },
    "include_chapter_titles_in_canonical_text": {
      "type": "boolean",
      "default": true
    },
    "include_section_titles_in_canonical_text": {
      "type": "boolean",
      "default": false
    },
    "max_epub_size_bytes": {
      "type": "integer",
      "minimum": 1,
      "default": 104857600,
      "maximum": 1073741824
    },
    "max_html_document_size_bytes": {
      "type": "integer",
      "minimum": 1,
      "default": 10485760,
      "maximum": 104857600
    },
    "max_text_block_chars": {
      "type": "integer",
      "minimum": 1,
      "default": 100000,
      "maximum": 1000000
    },
    "pipeline_timeout_seconds": {
      "type": "integer",
      "minimum": 1,
      "default": 120,
      "maximum": 3600
    },
    "html_parse_timeout_seconds": {
      "type": "integer",
      "minimum": 1,
      "default": 20,
      "maximum": 300
    },
    "max_archive_uncompressed_bytes": {
      "type": "integer",
      "minimum": 1,
      "default": 524288000,
      "maximum": 2147483648
    },
    "max_archive_entry_count": {
      "type": "integer",
      "minimum": 1,
      "default": 10000,
      "maximum": 100000
    },
    "max_archive_compression_ratio": {
      "type": "integer",
      "minimum": 1,
      "default": 100,
      "maximum": 1000
    },
    "max_toc_depth": {
      "type": "integer",
      "minimum": 1,
      "default": 8,
      "maximum": 64
    },
    "max_diagnostic_count": {
      "type": "integer",
      "minimum": 1,
      "default": 1000,
      "maximum": 100000
    },
    "max_output_json_bytes": {
      "type": "integer",
      "minimum": 1,
      "default": 524288000,
      "maximum": 1073741824
    },
    "include_debug": {
      "type": "boolean",
      "default": false
    }
  }
}
```

Default effective config:

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

Rules:

- A missing config is equivalent to `{}` and must use the defaults above.
- Config validation happens before input EPUB parsing.
- Library invalid config returns a structured failed result with `error.code = "invalid_config"`.
- CLI invalid config exits with code `4` and returns a structured failed result when the configured output channel is available.
- `--include-debug` is equivalent to setting effective config field `include_debug = true` for that CLI invocation.
- `--pretty` is a CLI formatting option only and must not be stored in config or affect semantic output.
- JSON Schema `default` values are documentation and validation metadata only; application code MUST apply defaults explicitly after config validation succeeds.
- Numeric config values MUST be JSON numbers with integer values. String units such as `"100MB"`, floats, `NaN`, and infinities are invalid.
- Resource limit fields have hard schema maximums. Values above those maximums are invalid config, even if the host machine could theoretically process them.

Hard maximums for v3.0:

| Config field | Maximum | Rationale |
|---|---:|---|
| `max_epub_size_bytes` | `1073741824` | 1 GiB input-file cap |
| `max_html_document_size_bytes` | `104857600` | 100 MiB per HTML document cap |
| `max_text_block_chars` | `1000000` | 1 million Unicode code points per text block |
| `pipeline_timeout_seconds` | `3600` | 1 hour whole-pipeline cap |
| `html_parse_timeout_seconds` | `300` | 5 minutes per HTML document cap |
| `max_archive_uncompressed_bytes` | `2147483648` | 2 GiB aggregate uncompressed archive cap |
| `max_archive_entry_count` | `100000` | 100k ZIP entries cap |
| `max_archive_compression_ratio` | `1000` | ZIP bomb guard cap |
| `max_toc_depth` | `64` | Deep recursion guard |
| `max_diagnostic_count` | `100000` | Bounded diagnostics output |
| `max_output_json_bytes` | `1073741824` | 1 GiB serialized JSON cap |

#### 4.1.2 Config input and version policy

The public library accepts config as one of:

- `None`;
- a JSON-serializable `dict[str, object]`;
- an `EpubContentExtractorConfig` dataclass or equivalent typed model whose serialized form validates against `schema/epub_content_extractor_config.v3.0.schema.json`.

Rules:

- The config schema is the normative validation contract for config input.
- The input config object MAY include optional `$schema` for editor/tooling support.
- `$schema` MUST be a string URI.
- `$schema` is allowed only in input config.
- `$schema` MUST be ignored by semantic config processing.
- `$schema` MUST NOT appear in `extraction.config`.
- `$schema` MUST NOT affect defaults, validation order, diagnostics, extraction behavior, or output.
- The config object may include optional `config_version` only if the config schema explicitly allows it in a future version. In v3.0 it is not allowed.
- Unknown config fields other than `$schema` are invalid because the schema is closed with `additionalProperties: false`.
- Config validation MUST happen before EPUB path validation and before EPUB parsing.
- Config defaults MUST be applied only by application code after validation succeeds, except for the invalid-config failed-result snapshot policy below.

#### 4.1.3 Invalid config structured result policy

When config validation fails, a structured failed result is still emitted when the selected output channel is available.

Rules:

- Library mode returns `status = "failed"`.
- CLI mode exits `4` if the failed result can be written to the selected output channel.
- `error.code` MUST be `invalid_config`.
- `error.recoverable` MUST be `false`.
- EPUB path validation and EPUB parsing MUST NOT start.
- `extraction.config` MUST contain the default effective config snapshot, not the raw invalid config.
- Raw invalid config values MUST NOT be included in normal production output.
- Raw invalid config values MAY be included only in redacted debug data when `include_debug = true` can be determined safely from trusted CLI flags or already-validated defaults. Otherwise raw invalid config MUST be omitted.
- `extraction.summary` MUST contain zero counts except `error_count = 1`.
- Invalid config output MUST validate against the official result schema.

#### 4.1.4 EPUB input validation, symlink, and permission policy

The `.epub` filename extension is advisory and is not a validation criterion in v3.0.

A file with a non-`.epub` extension MAY be accepted if it is a readable ZIP-based EPUB container and all EPUB package and archive-security checks pass. A file with a `.epub` extension MUST still fail with `input_not_epub` if it cannot be opened as a ZIP-based EPUB container.

Validation order after config validation:

1. Resolve the input path according to platform filesystem semantics without exposing the absolute path in production output.
2. If the path does not exist, fail with `input_file_not_found`.
3. If the path exists but is not a regular file, fail with `input_not_file`.
4. If the path is a symlink, follow the symlink only if the final target is a regular local file. Broken symlinks fail with `input_file_not_found`. Symlinks to directories or special files fail with `input_not_file`.
5. If the file cannot be read because of permissions or OS access errors, fail with `epub_open_failed`.
6. If file bytes exceed `max_epub_size_bytes`, fail with `epub_file_too_large` before opening the EPUB container.
7. If the file cannot be opened as a ZIP-based EPUB container at all, fail with `input_not_epub`.
8. If the ZIP container opens, run archive safety checks before locating or parsing OPF/package metadata.
9. If archive safety checks fail, fail with `epub_archive_security_violation`.
10. If archive safety checks pass but required EPUB package metadata cannot locate or parse the OPF/package document, fail with `epub_manifest_unreadable`.

A valid ZIP file that is not a valid EPUB container MUST NOT be accepted as EPUB input. It maps to `epub_manifest_unreadable` only when ZIP opening succeeds, archive safety checks pass, and EPUB package metadata is absent or unusable.

If both an archive security violation and missing/unreadable EPUB manifest are true, `epub_archive_security_violation` takes precedence. Implementations MUST NOT parse OPF/package XML, HTML, SVG, CSS, or manifest-referenced content before archive safety checks have passed.

### 4.1.5 Library API runtime type, mutability, and programmer-error policy

`EpubContentExtractionResult` is a public type name for a JSON-compatible plain Python `dict[str, object]` result shape. Implementations MAY provide `TypedDict` definitions or dataclass/Pydantic helpers internally, but the canonical public return value of `extract_epub_content()` MUST be a plain JSON-serializable mapping that validates against the official result schema.

Rules:

- Returned result objects are caller-owned mutable dictionaries. The extractor MUST NOT mutate a result after returning it.
- `extract_epub_content()` MUST be thread-safe for concurrent calls with independent inputs and configs. It MUST NOT rely on unsynchronized global mutable extraction state.
- Concurrent calls with the same input bytes, extractor version, config, and dependency versions MUST be semantically deterministic, except for timestamps and duration fields.
- `input_path` values of type `str` and `pathlib.Path` are accepted.
- `input_path = None` or any non-`str`/non-`Path` value is a programmer error and MUST raise `TypeError`.
- An empty string path, whitespace-only string path, or path containing a NUL character is treated as invalid local path input and MUST produce a structured failed result with `error.code = "input_file_not_found"` without exposing the raw path.
- Programmer errors are not normal extraction outcomes and are not represented as `EpubContentExtractionResult`.

The v3.0 public API does not expose schema-validation helper functions as stable API. Callers that need validation should use the published JSON Schema artifacts directly.

### 4.2 Canonical text builder

The extractor returns a structured book, not a top-level full-text field.

Downstream canonical text must be built explicitly from the structured book:

```python
from epub_content_extractor import build_canonical_text

text = build_canonical_text(
    book: EpubBook,
    options: EpubCanonicalTextBuildOptions | None = None,
) -> str
```

Rules:

- `EpubBook` does not contain `text`.
- `chapter.text` does not include `chapter.title`.
- `section.text` does not include `section.title`.
- Canonical text is derived from `front_matter`, `chapters`, `back_matter`, and optional footnotes according to build options.
- The builder must be deterministic.

### 4.3 CLI command

The canonical CLI command is:

```bash
epub-content-extractor extract INPUT.epub [options]
```

Supported options:

```bash
--output PATH                 Write JSON result object to PATH instead of stdout.
--config PATH                 Read extractor config from JSON file. Use `-` to read config JSON from stdin.
--pretty                      Pretty-print JSON output.
--include-debug               Include optional implementation debug data.
--version                     Print CLI version.
--help                        Print help.
```

The CLI must output the same structured result object as the Python library for extraction attempts that reach result construction.

Rules:

- If `--output` is provided, the JSON object is written to the given file.
- If `--output` is omitted, the JSON object is written to stdout.
- `--output -` is equivalent to stdout.
- If `--config -` is provided, config JSON is read from stdin before any JSON result is written. This is valid even when output is stdout.
- stdout is reserved for machine-readable JSON, except for `--version` and `--help`.
- Human-readable logs, if enabled, must be written to stderr.
- Human-readable logs are disabled by default for successful extraction.
- `--include-debug` includes a top-level `debug` object but does not enable human-readable logs by itself.
- `--pretty` affects JSON whitespace and key indentation only; it must not change fields, values, ordering guarantees, diagnostics, counts, or semantics.
- `--version` prints only the extractor CLI version string to stdout and exits `0`; it must not read input, run extraction, or emit an extraction result object.
- `--help` prints help text to stdout and exits `0`; it must not emit an extraction result object.
- CLI parser errors, missing required arguments, and invalid options print human-readable usage/error text to stderr and exit `2` without emitting a JSON result object.

### 4.4 CLI exit codes

| Exit code | Meaning |
|---:|---|
| `0` | Extraction finished with `status: "succeeded"`. Warnings may still exist in diagnostics. |
| `1` | Extraction finished with `status: "failed"`. The JSON result still follows the error schema. |
| `2` | CLI usage error, for example missing input argument or invalid option. No JSON result object is emitted. |
| `3` | Output write failure. No JSON result object is emitted when the selected output channel is unavailable. |
| `4` | Invalid config file or config schema validation failure. JSON failed result is emitted when the configured output channel is available. |
| `99` | Unexpected internal error. JSON failed result is emitted only if result construction and the selected output channel are still available. |

Additional rules:

- Exit code `2` is outside the extraction-result contract and returns only human-readable stderr.
- Exit code `4` should return a structured failed result with `error.code = "invalid_config"` when stdout or `--output` can be written.
- Exit code `3` means the selected JSON output destination cannot be written; therefore the CLI must not attempt to return the JSON result object through stdout as a fallback when `--output` was requested.
- For exit code `3`, stderr contains only a concise human-readable message safe for logs.

### 4.5 CLI execution and failure precedence

CLI execution order is deterministic:

1. Parse CLI arguments.
2. Handle `--help` and `--version`.
3. Read and validate config.
4. Validate input path and file preconditions.
5. Run extraction.
6. Serialize result JSON.
7. Write result JSON to the selected output channel.

Rules:

- Usage/parser errors exit `2` before config or input validation.
- `--help` and `--version` exit `0` without reading config, validating input, or constructing an extraction result.
- Invalid config has precedence over input validation failures.
- If writing to the selected output channel fails, CLI exits `3` regardless of the prepared extraction result status.
- When `--output PATH` is requested, the CLI MUST NOT fall back to stdout.
- Parent directories for `--output PATH` MUST already exist. The CLI MUST NOT create parent directories implicitly.
- `--output -` is supported and means stdout.
- `--config -` is supported and means stdin. The CLI reads stdin completely for config before constructing or writing the result.
- A missing `--config PATH`, unreadable config file, malformed UTF-8 config file, invalid JSON config file, or schema-invalid config all map to `invalid_config` and CLI exit `4` when the selected output channel is available.
- If `--output PATH` already exists, the CLI MUST overwrite it atomically. It MUST write the JSON bytes to a temporary file in the same directory, flush/close it, and then replace the destination path using the platform's atomic replace operation when available.
- If the destination path cannot be replaced atomically, the CLI MUST fail with exit `3` rather than risk a partial production JSON file.
- If stdout is the selected output channel and the stdout pipe is closed, CLI exits `3` and may emit only a concise safe message to stderr if stderr is available.
- `max_output_json_bytes` is measured as the exact number of UTF-8 bytes in the final JSON representation selected for output, including pretty-print whitespace when `--pretty` is used. Compact and pretty output must parse to identical objects, but they may have different byte lengths for this limit.
- JSON serialization is part of the extraction-result contract. If serialization fails because of an implementation defect, CLI exits `99`. If serialization would exceed `max_output_json_bytes`, extraction fails with `internal_error` in v3.0 because no dedicated `output_json_too_large` error code exists. This is a known v3.0 compatibility compromise; a future schema version SHOULD add `output_json_too_large` as a dedicated fatal error code.

Examples:

- Invalid option plus invalid config exits `2` and emits no JSON.
- `--version` with a missing input path exits `0` and emits no JSON result.
- Invalid config plus unwritable `--output` prepares an `invalid_config` result but exits `3` because the selected output channel is unavailable.

---

## 5. Official output mode

The only official output mode is **structured object output**.

Plain text output is not an official extraction result mode.

There is no successful response shape that consists only of text.

If plain text is needed, the caller must use:

```python
build_canonical_text(book, options)
```

Rationale: the extractor output should model the book as structured data. A single full-text field at the book level creates duplication, risks desynchronization, and makes the output less useful for downstream document-level processing.

---

## 6. Top-level result object

```typescript
type EpubExtractionStatus = "succeeded" | "failed";

type DiagnosticSeverity = "info" | "warning" | "error";

interface EpubContentExtractionResult {
  schema_version: "epub_content_extractor.v3.0";
  status: EpubExtractionStatus;

  /** Present only when status === "succeeded". */
  book?: EpubBook;

  /** Present only when status === "failed". */
  error?: EpubExtractionError;

  diagnostics: EpubDiagnostic[];
  extraction: EpubExtractionInfo;

  /** Present only when effective config include_debug === true. */
  debug?: EpubDebugInfo;
}
```

The official result schema is `schema/epub_content_extractor.v3.0.schema.json`.

Rules:

- The JSON Schema file is the normative machine-validation artifact for production output.
- The TypeScript-like interfaces in this document are explanatory and must remain consistent with the schema.
- The normal production result must not include fields outside the schema.
- Runtime production output validation against the result schema is optional and disabled by default for performance.
- CI, contract tests, fixture tests, and release validation must validate representative production outputs against the official result schema.

### 6.1 Normative result JSON Schema requirement

`schema/epub_content_extractor.v3.0.schema.json` is a required normative artifact for v3.0.

Code generation, release builds, and contract tests MUST NOT rely only on the TypeScript-like interfaces in this document. The JSON Schema MUST define:

- required fields for succeeded and failed results;
- mutually exclusive `book` and `error` using `oneOf` or equivalent validation;
- `additionalProperties` behavior for every production object;
- all enum values;
- all nullable and optional fields;
- timestamp formats;
- numeric minimums and maximum-sensitive constraints;
- array item schemas;
- debug field openness policy.

A release is invalid if examples in this document do not validate against `schema/epub_content_extractor.v3.0.schema.json`.

### 6.1.1 Normative schema and registry artifact locations

The normative machine-readable artifacts for contract version v3.0 MUST be stored at these repository paths:

```text
schema/epub_content_extractor.v3.0.schema.json
schema/epub_content_extractor_config.v3.0.schema.json
schema/epub_content_extractor_diagnostic_registry.v3.0.json
schema/epub_content_extractor_error_registry.v3.0.json
schema/epub_content_extractor_diagnostic_registry.v3.0.schema.json
schema/epub_content_extractor_error_registry.v3.0.schema.json
schema/epub_content_extractor_fixture_manifest.v3.0.schema.json
schema/epub_content_extractor_golden_acceptance_manifest.v3.0.schema.json
schema/epub_canonical_text_build_options.v3.0.schema.json
schema/epub_content_extractor_test_coverage_manifest.v3.0.schema.json
```

The golden-output acceptance manifest is stored under:

```text
docs/testing/epub_content_extractor_golden_acceptance_manifest.v3.0.json
```

The test coverage manifest is stored under:

```text
docs/testing/epub_content_extractor_test_coverage_manifest.v3.0.json
```

The canonical text builder options schema is stored under:

```text
schema/epub_canonical_text_build_options.v3.0.schema.json
schema/epub_content_extractor_test_coverage_manifest.v3.0.schema.json
```

Artifact path resolution policy:

- all release-validation paths are resolved from the explicit repository root passed as `--repo-root`;
- the prose shorthand `schema/<file>` means `docs/architecture/schema/<file>` relative to repository root;
- executable test fixtures under `tests/fixtures/...` are repository-root-relative and are not resolved through the `schema/` alias;
- release validation MUST fail when a `schema/<file>` prose reference cannot be resolved through this alias policy.

The files under `docs/architecture/` are explanatory documentation unless they are exact synchronized copies of the files above. CI, release validation, and generated tests MUST load schemas and registries from `docs/architecture/schema/` via the `schema/` alias policy.

### Config `$schema` URI assertion policy

The input config field `$schema` is an optional tooling-only field, but when present it MUST be an absolute URI. Contract tests and production validation MUST use the same assertion behavior.

Because JSON Schema Draft 2020-12 validators may treat `format: "uri"` as annotation unless format assertions are enabled, the config schema also constrains `$schema` with a scheme-prefix pattern. CI and contract tests SHOULD still enable URI format assertions where the selected validator supports them.

A release is invalid if any of these disagree:

- documented contract version;
- physical artifact file names;
- `$id` values in JSON Schema files;
- `schema_version` / `registry_version` constants inside registry files;
- result-schema diagnostic and error enums;
- diagnostic and error registry code sets.

### 6.2 JSON field presence, nullable, and empty-string policy

The output JSON contract distinguishes nullable fields from optional fields.

Rules:

- A field typed as `T | null` is required in the containing object and MUST be emitted with either a value of type `T` or `null`.
- A field marked with `?` is optional and MUST be omitted when unknown or not applicable.
- Optional fields MUST NOT be emitted as `null` unless the JSON Schema explicitly declares `type: [T, "null"]`.
- The word `undefined` is explanatory TypeScript-like notation only and MUST NOT appear in JSON output.
- Empty strings after cleanup MUST NOT be emitted for nullable metadata/title fields. Emit `null` for required nullable fields and omit optional string fields.
- Empty strings MUST NOT be emitted for required text-bearing fields such as paragraph `text`, chapter `text`, section `text`, and footnote `text`. Empty text-bearing units are removed before final output.
- Empty arrays are emitted as `[]` when the array field is required.

Specific v3.0 policy:

- `book.title` and `book.subtitle` are required and nullable.
- `metadata.publisher`, `metadata.published_at`, `metadata.modified_at`, `metadata.description`, and `metadata.rights` are required and nullable.
- `chapter.title`, `section.title`, `footnote.marker`, `footnote.paragraph_number`, `toc.target_id`, `toc.chapter_number`, `asset.file_name`, `asset.alt_text`, and `identifier.scheme` are optional and omitted when unknown or not applicable.
- `metadata.source_file.file_name` and `metadata.source_file.epub_version` are optional; `metadata.source_file.sha256` and `metadata.source_file.size_bytes` are required for successful local extraction.

### 6.3 Success invariant

When `status === "succeeded"`:

- `book` must exist;
- `error` must be absent;
- `book.language` must be `"en"`;
- `diagnostics` may contain `info` and `warning` diagnostics;
- successful results MUST NOT contain diagnostics with `severity = "error"`;
- at least one chapter or front/back matter section must contain readable text.

#### 6.3.1 Readable-content success invariant

A result with `status = "succeeded"` MUST contain at least one readable content container.

Readable content containers in v3.0 are:

- a chapter with `text.length > 0`;
- a front/back matter section with `paragraphs.length > 0` and `text.length > 0`.

A result with `status = "succeeded"` and no readable content container is invalid. It MUST instead be emitted as `status = "failed"` with `error.code = "no_readable_content"` and `error.recoverable = false`.

Rules:

- `chapter.text` MUST have `minLength: 1` in the result schema.
- `section.text` MUST have `minLength: 1` in the result schema unless a future schema version explicitly introduces structural-only section types.
- A successful result MAY contain only front matter or only back matter when that section is the only readable book content.
- A successful result MUST NOT rely only on book-level or detached footnotes as readable content. At least one chapter must contain non-empty `chapter.text`, or at least one front/back matter section must contain non-empty paragraph text.
- Schema validation and contract tests MUST reject successful outputs with no readable content container.

### 6.4 Failure invariant

When `status === "failed"`:

- `error` must exist;
- `book` must be absent;
- partial book output must not be included in normal mode;
- partial debug data may be included only under top-level `debug` when explicitly enabled;
- `diagnostics` must exist and be an array;
- `extraction` must exist when a structured result object is emitted;
- CLI must exit with a non-zero exit code.

### 6.5 Arrays in failed results

`front_matter`, `chapters`, `back_matter`, `footnotes`, `table_of_contents`, and `assets` are fields of `book`.

Because `book` is absent in failed results, those arrays are also absent in normal failed results. Partial arrays may appear only under top-level `debug` when `include_debug = true`.

---

## 7. Book object

`EpubBook` is the main output object. It describes the extracted book itself, not the extractor's internal processing state.

```typescript
interface EpubBook {
  title: string | null;
  subtitle: string | null;

  /** Always "en". */
  language: EpubBookLanguage;

  authors: EpubPerson[];
  contributors: EpubPerson[];

  metadata: EpubBookMetadata;

  front_matter: EpubBookSection[];
  chapters: EpubChapter[];
  back_matter: EpubBookSection[];

  /** Footnotes/endnotes that cannot be confidently assigned to a chapter or section. */
  footnotes: EpubFootnote[];

  table_of_contents: EpubTocItem[];

  /** Lightweight metadata about images/assets. No binary data. */
  assets: EpubAsset[];
}
```

Rules:

- `EpubBook` must not contain a full clean text field.
- All readable text must live inside `front_matter[]`, `chapters[]`, `back_matter[]`, and `footnotes[]`.
- In successful results, `front_matter`, `chapters`, `back_matter`, `footnotes`, `table_of_contents`, and `assets` must always be emitted as arrays, even when empty.
- Empty arrays must be emitted as `[]`, not omitted.
- `title` must be emitted as a string when known and as `null` when missing.
- `subtitle` must be emitted as a string when known and as `null` when missing.
- Missing scalar metadata values may be `null` only where explicitly allowed in the relevant interface.

---

## 8. Metadata

```typescript
interface EpubBookMetadata {
  identifiers: EpubIdentifier[];

  publisher: string | null;
  published_at: string | null;
  modified_at: string | null;

  description: string | null;
  rights: string | null;

  subjects: string[];

  source_file: EpubSourceFile;
}
```

```typescript
interface EpubIdentifier {
  scheme?: string;
  value: string;
}
```

```typescript
interface EpubSourceFile {
  file_name?: string;
  sha256: string;
  size_bytes: number;
  epub_version?: string;
}
```

Rules:

- EPUB without title metadata is valid.
- EPUB without author metadata is valid.
- EPUB without publisher metadata is valid.
- EPUB without language metadata is valid because output language is fixed to `"en"`.
- Missing metadata should produce diagnostics when useful, but must not fail extraction by itself.
- `metadata.identifiers` and `metadata.subjects` must always be arrays and must not be `null`.
- Nullable metadata scalar fields are exactly `publisher`, `published_at`, `modified_at`, `description`, and `rights`.
- `source_file` MUST be emitted for successful extraction from the canonical local-file API. It must be an object and must not be `null`.
- Future non-local APIs MAY make `source_file` optional only through a versioned schema change.
- `source_file.file_name` may be included.
- Absolute local file paths must not be included by default.
- For successful extraction from a local readable input file, `source_file.sha256` MUST be emitted and MUST be the lowercase hexadecimal SHA-256 digest of the input file bytes before EPUB parsing.
- `source_file.size_bytes` MUST be emitted for successful extraction from a local readable input file.
- `source_file.file_name`, when emitted, MUST be the basename only and MUST NOT include absolute or parent directory path components.
- `source_file.epub_version` MAY be emitted when it can be determined from EPUB package metadata.

### 8.1 Duplicate metadata and source value handling

Rules:

- Duplicate `metadata.identifiers` with the same normalized `scheme` and `value` MUST be deduplicated while preserving first-seen order.
- Duplicate `metadata.subjects` MUST be deduplicated case-insensitively after trimming, while preserving the first emitted spelling.
- Duplicate authors/contributors from repeated metadata entries MUST be deduplicated by normalized `(name, role)` while preserving first-seen order.
- Empty metadata values after trimming are treated as missing.
- Raw duplicate metadata values MUST NOT be emitted only to preserve source verbosity.

### 8.2 Date normalization and validation

`published_at` and `modified_at` must be normalized deterministically.

Accepted input forms:

- ISO-8601/RFC-3339 date: `YYYY-MM-DD`;
- ISO-8601/RFC-3339 date-time with timezone;
- EPUB/OPF date strings that can be losslessly normalized to one of the forms above.

Output rules:

- Date-only values are emitted as `YYYY-MM-DD`.
- Date-time values are emitted as UTC RFC-3339 with `Z`, for example `2026-05-08T10:00:00Z`.
- Leading and trailing whitespace is removed before validation.
- Invalid dates must not be emitted as raw strings in normal output.
- Invalid or unparseable dates are emitted as `null` and produce diagnostic `metadata_date_invalid` with severity `warning`.
- Raw invalid date strings may appear only in redacted debug data when `include_debug = true`.

---

## 9. Authors and contributors

```typescript
interface EpubPerson {
  name: string;

  role:
    | "author"
    | "editor"
    | "translator"
    | "illustrator"
    | "contributor"
    | "unknown";
}
```

Rules:

- Multiple authors must be represented as multiple `EpubPerson` objects.
- Multiple authors must not be joined into a single string when metadata clearly separates them.
- If EPUB metadata contains one ambiguous creator string with several names, splitting is allowed only with high confidence.
- If splitting is uncertain, preserve the original string as one author and emit diagnostic `metadata_author_split_uncertain` with severity `warning`.
- Translators should go to `contributors[]` with `role: "translator"` unless the EPUB metadata explicitly treats them as authors.

### 9.1 Author split confidence policy

Author splitting must be deterministic.

High-confidence split cases:

- EPUB metadata provides multiple separate creator elements;
- one creator string uses semicolon, pipe, or newline delimiters and every resulting part is name-shaped;
- one creator string uses ` and ` or ` & ` between two to four name-shaped parts and contains no role phrase.

A part is name-shaped when:

- it contains at least two alphabetic characters;
- it is not only a role label such as `editor`, `translator`, `illustrator`, `by`, or `with`;
- it is not mostly punctuation or digits.

Comma is not a high-confidence author delimiter by itself because it is common in `Last, First` names.

If an implementation uses numeric confidence, it must split only when `confidence >= 0.85`. Otherwise it must preserve the original string as one author and emit `metadata_author_split_uncertain`.

---

## 10. Front matter and back matter sections

```typescript
type EpubBookSectionType =
  | "cover"
  | "title_page"
  | "copyright"
  | "dedication"
  | "epigraph"
  | "preface"
  | "foreword"
  | "introduction"
  | "prologue"
  | "appendix"
  | "notes"
  | "endnotes"
  | "bibliography"
  | "index"
  | "publisher_notes"
  | "advertisement"
  | "unknown";
```

```typescript
interface EpubBookSection {
  id: string;
  type: EpubBookSectionType;

  title?: string;

  /** Full clean section text. Does not include title. */
  text: string;

  paragraphs: EpubParagraph[];
  footnotes: EpubFootnote[];

  /** Whether this section is included by default when building canonical downstream text. */
  included_in_canonical_text: boolean;
}
```

Rules:

- Front matter and back matter must be preserved in output when detected.
- They may be excluded from canonical text by default.
- `section.title` is stored separately.
- `section.text` must not include `section.title`.
- `section.text` must be deterministically buildable from `section.paragraphs[].text` using `"\n\n"`.
- `section.text` and every `section.paragraphs[].text` MUST be non-empty after cleanup. Empty sections are removed rather than emitted.
- Copyright, advertisements, publisher notes, bibliography, and index sections should be preserved structurally when detected, but `included_in_canonical_text` must default to `false`.
- Navigation boilerplate, repeated headers/footers, page numbers, and empty layout artifacts may be removed completely.

---

## 11. Chapters

The term `chapter` is a convenient main-content container. It can represent a conventional chapter, part, act, scene, or generic section.

```typescript
type EpubChapterType =
  | "chapter"
  | "part"
  | "act"
  | "scene"
  | "section"
  | "unknown";
```

```typescript
interface EpubChapter {
  id: string;
  chapter_number: number;

  type: EpubChapterType;
  title?: string;

  /** Full clean chapter text. Does not include title. */
  text: string;

  footnotes: EpubFootnote[];
}
```

Rules:

- `chapter_number` is 1-based and follows reading order.
- `chapter.id` is an internal stable output id such as `chapter_001`.
- `chapter.id` must not expose EPUB href, spine id, or raw file path.
- `chapter.title` is stored separately.
- `chapter.text` must not include `chapter.title`.
- `chapter.text` is the authoritative public chapter body field.
- The production schema MUST NOT include `paragraphs` inside `chapters[]` items.
- Chapter paragraph-like segmentation MAY exist internally for extraction, cleanup, footnote linking, and debug output, but it MUST NOT appear in normal production output.
- `chapter.text` MUST be non-empty after cleanup. Empty chapters are removed rather than emitted.
- Footnote text must not be included in `chapter.text`.

### 11.1 Chapter detection

Chapter detection uses a hybrid strategy:

1. If EPUB TOC is valid and useful, build chapters from TOC in reading order.
2. If TOC is missing or not useful, build chapters from spine reading order.
3. If one spine HTML document contains multiple strong headings (`h1`, `h2`, or equivalent), it may be split into multiple chapters.
4. If a chapter title cannot be confidently detected, omit `title`.
5. If semantic type can be inferred, set `type` to `"chapter"`, `"part"`, `"act"`, `"scene"`, or `"section"`; otherwise use `"unknown"`.

---

## 12. Paragraphs

```typescript
interface EpubParagraph {
  text: string;
}
```

Rules:

- Public `EpubParagraph` objects are emitted only inside `front_matter[].paragraphs[]` and `back_matter[].paragraphs[]`.
- Chapter paragraph segmentation is internal in v3.0 and is represented publicly only by `chapter.text`.
- The main schema MUST NOT include `chapters[].paragraphs`.
- The main schema must not include source offsets, raw block ids, scoring, classification features, or confidence values.
- `sentences[]` are not part of v3.0 output.
- `sentence_count` is not part of the main schema.
- `has_dialogue` is not part of the main schema.
- Sentence segmentation belongs to downstream NLP modules.
- Lists (`li`) in front/back matter should be preserved as separate paragraphs when they contain meaningful readable text.
- Lists (`li`) in chapters should be preserved as readable text inside `chapter.text` without exposing chapter paragraph objects.
- Broken paragraph-like blocks may be merged during post-processing.

---

## 13. Footnotes and endnotes

```typescript
interface EpubFootnote {
  id: string;
  marker?: string;
  text: string;

  /** Optional approximate semantic link. 1-based paragraph number inside the owning chapter/section. */
  paragraph_number?: number;
}
```

Rules:

- Footnotes must be stored near their owner when ownership is clear:
  - chapter-level footnotes in `chapter.footnotes[]`;
  - front/back matter footnotes in `section.footnotes[]`.
- Footnotes that cannot be confidently assigned must be stored in `book.footnotes[]`.
- `footnote.id` is an internal stable output id such as `footnote_001`.
- Footnote text must not be included in `chapter.text` or `section.text` by default.
- Inline footnote markers should be removed from paragraph text only when confidently resolved to a footnote.
- Unresolved inline markers must remain in paragraph text and produce diagnostic `footnote_marker_unresolved`.
- `paragraph_number` is optional for every footnote, including chapter-level footnotes.
- `paragraph_number` must be emitted only when the extractor can link the footnote to a specific final paragraph.

Mandatory marker forms for v3.0:

- bracketed numeric markers: `[1]`, `[2]`, `[123]`;
- parenthesized numeric markers: `(1)`, `(2)`, `(123)`;
- superscript numeric markers represented by EPUB/HTML markup such as `<sup>1</sup>`;
- linked numeric markers where an anchor target clearly resolves to a footnote/endnote;
- single symbolic markers: `*`, `†`, `‡`.

### 13.1 Paragraph numbering after cleanup

`paragraph_number` is calculated after final paragraph cleanup, paragraph deletion, and paragraph merge.

Rules:

- For section-owned footnotes, numbering is 1-based inside the owning `section.paragraphs[]` array.
- For chapter-owned footnotes, numbering is 1-based inside the final internal chapter paragraph-like sequence used to assemble `chapter.text`; this sequence is not exposed as `chapters[].paragraphs` in production output.
- If an inline marker was removed from a paragraph-like unit, `paragraph_number` points to the final unit that contained that marker before removal.
- If several source paragraph-like units are merged, the footnote points to the merged final unit.
- If the owner is known but no exact paragraph link is known, omit `paragraph_number` without failing extraction.

### 13.2 Duplicate markers

Duplicate footnote markers in the same chapter or section are ambiguous.

Rules:

- If duplicate markers have unique hyperlink targets, the extractor may resolve by target id.
- If duplicate markers cannot be disambiguated by a unique target, inline markers must remain in paragraph text.
- Ambiguous duplicate markers produce `footnote_duplicate_marker` with severity `warning`.
- Any unresolved inline marker also produces `footnote_marker_unresolved`.
- Multiple plain `*` markers in the same chapter or section must not be resolved by marker text alone. They may be resolved only through a unique hyperlink or explicit footnote target.

---

## 14. Table of contents

```typescript
interface EpubTocItem {
  title: string;

  type:
    | "front_matter"
    | "chapter"
    | "back_matter"
    | "unknown";

  /** Internal id of target chapter or section, if confidently resolved. */
  target_id?: string;

  /** Present when this item points to a chapter. */
  chapter_number?: number;

  children: EpubTocItem[];
}
```

Rules:

- TOC should be preserved when present.
- TOC item targets should use internal output ids, not EPUB hrefs.
- If target resolution is uncertain, keep the TOC item without `target_id` and emit diagnostic `toc_target_unresolved`.
- TOC text itself must not be included in canonical downstream text by default.
- `children` must always be emitted as an array.
- Nested TOC children are resolved independently from their parent.
- If a parent target is unresolved but a child target is resolved, preserve the parent without `target_id`, emit `toc_target_unresolved` for the parent, and keep the resolved child target.
- TOC nesting deeper than `max_toc_depth` MUST be flattened deterministically at the configured depth by attaching deeper descendants to the deepest allowed parent in reading order and emitting `quality_warning` with severity `warning`.

---

## 15. Assets

`epub_content_extractor` does not extract binary image data, but may expose lightweight asset metadata.

```typescript
type EpubAssetType =
  | "cover"
  | "illustration"
  | "image"
  | "unknown";
```

```typescript
interface EpubAsset {
  type: EpubAssetType;
  media_type: string;
  file_name?: string;
  alt_text?: string;
}
```

Rules:

- No base64 image content in output.
- No binary files in output.
- Images may be listed as metadata only.
- CSS, fonts, and scripts are not represented as content assets unless explicitly needed for diagnostics.

---

## 16. Canonical text builder

Canonical text is not stored in `EpubBook`. It is derived by a dedicated builder.

The public builder accepts `options = None` or a partial mapping containing only the boolean keys below:

```typescript
interface EpubCanonicalTextBuildOptions {
  include_front_matter?: boolean;
  include_back_matter?: boolean;
  include_footnotes?: boolean;
  include_chapter_titles?: boolean;
  include_section_titles?: boolean;
}
```

Default public options:

```json
{
  "include_front_matter": false,
  "include_back_matter": false,
  "include_footnotes": false,
  "include_chapter_titles": true,
  "include_section_titles": false
}
```

The machine-readable public options contract is `schema/epub_canonical_text_build_options.v3.0.schema.json`. The schema is closed with `additionalProperties: false`; tests and generated clients SHOULD use it instead of inferring option names from prose.

Public option merging rules:

- `options = None` is equivalent to `{}`.
- Missing option keys use the defaults above.
- Every provided option value MUST be a boolean.
- Unknown option keys MUST raise `ValueError`.
- `separator_between_paragraphs` and `separator_between_chapters` are internal v3.0 constants, not accepted public option keys.
- Passing separator keys MUST raise `ValueError` in v3.0.
- The fixed paragraph separator is `"\n\n"`.
- The fixed chapter separator is `"\n\n\n"`.
- The builder MUST NOT mutate `book` or `options`.
- The builder MUST be deterministic.

General builder rules:

- The builder must use `chapter.text` directly for chapter body content.
- The builder must use `section.text` directly for front/back matter body content.
- The builder must join top-level canonical text containers with `"\n\n\n"`.
- When a title is included, the title and its body must be separated by `"\n\n"`.
- The builder must include titles only when corresponding title options are enabled.
- The builder must not mutate the book object.
- The builder must be deterministic.

### 16.1 Effective canonical text options from extractor config

`extraction.summary.canonical_text_chars` MUST be computed by calling `build_canonical_text(book, options)` with options derived from effective extractor config:

| Extractor config field | Builder option |
|---|---|
| `include_front_matter_in_canonical_text` | `include_front_matter` |
| `include_back_matter_in_canonical_text` | `include_back_matter` |
| `include_footnotes_in_canonical_text` | `include_footnotes` |
| `include_chapter_titles_in_canonical_text` | `include_chapter_titles` |
| `include_section_titles_in_canonical_text` | `include_section_titles` |

`separator_between_paragraphs` and `separator_between_chapters` use builder defaults in v3.0 and are not configurable through extractor config.

`EpubBookSection.included_in_canonical_text` represents structural eligibility, not the effective result of a particular builder invocation.

### 16.2 Canonical text builder invalid input policy

`build_canonical_text()` is a pure library helper, not an extraction attempt.

Rules:

- Invalid `book` argument is a programmer error.
- Invalid `options` argument is a programmer error.
- Public `options` may be a partial mapping containing only the five boolean option keys documented in Section 16.
- `options = None` MUST be treated exactly like an empty mapping.
- Non-boolean option values MUST raise `ValueError`.
- Separator option keys MUST raise `ValueError` even if their values equal the internal constants.
- Programmer errors MUST raise `TypeError` or `ValueError`.
- The builder MUST NOT return an `EpubContentExtractionResult`.
- The builder MUST NOT emit diagnostics.
- The builder MUST NOT mutate `book`.
- The builder MUST be deterministic for the same `book` and `options`.
- `book` MUST contain the required v3.0 fields needed by the builder, including `front_matter`, `chapters`, `back_matter`, and `footnotes`. Missing required fields are `ValueError`.
- Unknown option fields are `ValueError`.
- Custom separators are not accepted in v3.0 public options; callers must use the fixed default separators.

Examples:

- `build_canonical_text(None)` raises `TypeError`.
- Missing required `book.chapters` raises `ValueError`.
- Unknown option field raises `ValueError`.

---

## 17. Extraction info

```typescript
interface EpubExtractionInfo {
  extractor_version: string;

  started_at: string;
  finished_at: string;
  duration_ms: number;

  config: EpubExtractionConfigSnapshot;
  summary: EpubExtractionSummary;
}
```

```typescript
interface EpubExtractionConfigSnapshot {
  include_front_matter_in_canonical_text: boolean;
  include_back_matter_in_canonical_text: boolean;
  include_footnotes_in_canonical_text: boolean;
  include_chapter_titles_in_canonical_text: boolean;
  include_section_titles_in_canonical_text: boolean;

  max_epub_size_bytes: number;
  max_html_document_size_bytes: number;
  max_text_block_chars: number;
  pipeline_timeout_seconds: number;
  html_parse_timeout_seconds: number;

  max_archive_uncompressed_bytes: number;
  max_archive_entry_count: number;
  max_archive_compression_ratio: number;
  max_toc_depth: number;
  max_diagnostic_count: number;
  max_output_json_bytes: number;

  include_debug: boolean;
}
```

```typescript
interface EpubExtractionSummary {
  chapter_count: number;
  front_matter_section_count: number;
  back_matter_section_count: number;

  paragraph_count: number;
  footnote_count: number;

  /** Total clean text chars across extracted chapters and sections. */
  total_text_chars: number;

  /** Total chars produced by build_canonical_text using config defaults. */
  canonical_text_chars: number;

  removed_section_count: number;
  warning_count: number;
  error_count: number;
}
```

Rules:

- Extraction info may describe high-level extraction metadata.
- It must not expose raw blocks, source offsets, scoring internals, or raw HTML unless debug mode is explicitly enabled.
- `extractor_version` must be SemVer 2.0.0 compatible without a leading `v`, for example `3.0.0`, `3.0.1`, or `3.0.0-beta.1`.
- `started_at` and `finished_at` must be UTC RFC-3339 timestamps with `Z` when a structured result object is emitted.
- `finished_at` and `duration_ms` must always be present in emitted failed results.
- `duration_ms` is a non-negative integer.
- `summary` must always be present when a structured result object is emitted, including failed results.
- Early fatal failures must emit all summary fields with zero values except `error_count`, which must reflect the fatal error count.
- `extraction.config` is the effective semantic config snapshot. It MUST NOT contain input-only `$schema`.
- `extraction.config` values MUST satisfy the same numeric minimums and maximums as the official config schema, except that input-only tooling fields are omitted.

### 17.1 Summary counting rules

Text length is counted after Unicode normalization and final cleanup.

Rules:

- `canonical_text_chars` is the number of Unicode code points in the string returned by `build_canonical_text(book, effective canonical text config)`.
- In Python, this is equivalent to `len(canonical_text)` after normalization.
- `canonical_text_chars` is not byte length.
- `total_text_chars` is the number of Unicode code points across all preserved `text` fields in `front_matter[]`, `chapters[]`, and `back_matter[]`.
- `total_text_chars` includes preserved front matter and back matter even when those sections are excluded from canonical text.
- `total_text_chars` excludes book-level, chapter-level, and section-level footnote text because footnotes are stored separately.
- `total_text_chars` excludes removed sections and dropped blocks.
- `paragraph_count` is the total number of emitted `EpubParagraph` objects in `front_matter[].paragraphs[]` and `back_matter[].paragraphs[]`.
- `paragraph_count` excludes chapter paragraph-like units because `chapters[].paragraphs` is not part of the v3.0 production schema.
- `paragraph_count` excludes footnotes.
- `footnote_count` is the total number of footnotes in `book.footnotes[]`, every `chapter.footnotes[]`, and every front/back matter `section.footnotes[]`.

### 17.2 Warning and error count policy

`warning_count` MUST equal the number of emitted diagnostics with `severity = "warning"`.

`error_count` MUST equal:

```text
number of emitted diagnostics with severity = "error"
+ 1 if top-level error exists and is not already represented by one emitted error diagnostic
```

Rules:

- For early fatal failures with no diagnostics, `error_count` MUST be `1`.
- For successful results, `error_count` MUST be `0` because successful results MUST NOT emit `severity = "error"` diagnostics.
- `empty_readable_content` is an error diagnostic only when extraction reaches content analysis and determines that no readable content remains. If the top-level `error.code` is `no_readable_content` and `empty_readable_content` is emitted, it counts once, not twice.
- `warning_count` and `error_count` are computed after diagnostic truncation by `max_diagnostic_count`. If diagnostics are truncated, the last emitted diagnostic MUST be `quality_warning` describing truncation.

---

## 18. Diagnostics

```typescript
interface EpubDiagnostic {
  code: EpubDiagnosticCode;
  severity: "info" | "warning" | "error";
  message: string;

  /** Optional machine-readable affected entity metadata. */
  entity_type?:
    | "book"
    | "chapter"
    | "section"
    | "footnote"
    | "toc_item"
    | "asset"
    | "config"
    | "archive_entry"
    | "input_file";
  entity_id?: string;
  field?: string;
}
```

```typescript
type EpubDiagnosticCode =
  | "metadata_missing_title"
  | "metadata_missing_author"
  | "metadata_language_missing"
  | "metadata_language_conflicts_with_contract"
  | "metadata_author_split_uncertain"
  | "metadata_date_invalid"

  | "table_of_contents_missing"
  | "toc_target_unresolved"

  | "chapter_title_detected"
  | "chapter_title_uncertain"
  | "chapter_type_uncertain"

  | "front_matter_detected"
  | "back_matter_detected"

  | "copyright_section_detected"
  | "advertisement_section_detected"
  | "publisher_notes_detected"
  | "table_of_contents_removed_from_canonical_text"

  | "footnote_detected"
  | "footnote_marker_removed"
  | "footnote_marker_unresolved"
  | "footnote_owner_uncertain"
  | "footnote_duplicate_marker"

  | "page_number_removed"
  | "repeated_header_footer_removed"
  | "navigation_boilerplate_removed"
  | "artifact_removed"

  | "unicode_normalized"
  | "unicode_normalization_failed"

  | "html_document_too_large_skipped"
  | "html_document_parse_timeout_skipped"
  | "text_block_too_large_split"
  | "text_block_too_large_dropped"

  | "empty_readable_content"
  | "quality_warning";
```

Rules:

- Diagnostics are part of production output.
- Diagnostics must be concise and safe to log.
- Diagnostics must not contain full book text.
- Diagnostics must not contain full local file paths by default.
- Diagnostics should explain non-fatal losses or uncertain classifications.
- Diagnostics MAY include optional structured affected entity fields `entity_type`, `entity_id`, and `field`.
- `entity_id` MUST use internal stable ids, deterministic TOC item ids, safe relative EPUB paths, or safe config field names only. It MUST NOT expose absolute local paths or full raw text.
- `field` MUST be a stable schema/config field name when present.
- Consumers MUST NOT parse `message` to identify affected entities when structured fields are present.
- Diagnostics must have stable deterministic order.
- Stable order is pipeline event order first, reading order second, and deterministic code/id tie-breaker third.
- For the same input bytes, extractor version, config, and dependency versions, diagnostics order must be identical except for timestamp-independent implementation defects.

### 18.1 Diagnostic code matrix

The table below documents every diagnostic code carried by the v3.0 result schema. Whether a code may be emitted by production code is controlled by the normative diagnostic registry.

A diagnostic code with `coverage_status = "reserved_not_emitted_by_default"` is schema-reserved and MUST NOT be emitted by production code in v3.0, even if it appears in this matrix for schema completeness. A release-candidate registry MUST NOT contain `coverage_status = "requires_contract_decision"`; that status is allowed only in draft registries before a release decision is made.

Messages are human-readable and are not stable API. `code`, `severity`, deterministic ordering, count behavior, and registry coverage status are stable API.

| Diagnostic code | Severity | When emitted | Affected entity policy | Count impact | Can appear in success |
|---|---|---|---|---|---|
| `metadata_missing_title` | `warning` | No usable title metadata is available | no raw metadata value | warning +1 | yes |
| `metadata_missing_author` | `info` | No usable author metadata is available | no raw metadata value | none | yes |
| `metadata_language_missing` | `info` | EPUB language metadata is absent | no raw metadata value | none | yes |
| `metadata_language_conflicts_with_contract` | `warning` | Metadata language is present and primarily non-English-like | normalized language value only | warning +1 | yes |
| `metadata_author_split_uncertain` | `warning` | Ambiguous creator string cannot be split safely | no full raw metadata if long/private | warning +1 | yes |
| `metadata_date_invalid` | `warning` | Date metadata cannot be normalized losslessly | field name only | warning +1 | yes |
| `table_of_contents_missing` | `info` | EPUB has no usable TOC | no href | none | yes |
| `toc_target_unresolved` | `warning` | TOC item target cannot be mapped to an internal output id | TOC title or deterministic item id only | warning +1 | yes |
| `chapter_title_detected` | `info` | A chapter title is confidently detected from heading/TOC | internal chapter id only | none | yes |
| `chapter_title_uncertain` | `warning` | Chapter title candidate is ambiguous and omitted | internal chapter id only | warning +1 | yes |
| `chapter_type_uncertain` | `warning` | Chapter semantic type cannot be inferred | internal chapter id only | warning +1 | yes |
| `front_matter_detected` | `info` | A front matter section is detected | internal section id only | none | yes |
| `back_matter_detected` | `info` | A back matter section is detected | internal section id only | none | yes |
| `copyright_section_detected` | `info` | Copyright section is detected and structurally preserved/excluded from canonical text | internal section id only | none | yes |
| `advertisement_section_detected` | `warning` | Advertisement section is detected | internal section id only | warning +1 | yes |
| `publisher_notes_detected` | `info` | Publisher notes are detected | internal section id only | none | yes |
| `table_of_contents_removed_from_canonical_text` | `info` | TOC-like text is removed from canonical text | internal section/id only | none | yes |
| `footnote_detected` | `info` | Footnote/endnote is detected | internal footnote id only | none | yes |
| `footnote_marker_removed` | `info` | Inline marker is resolved and removed from paragraph text | internal footnote id and owner id only | none | yes |
| `footnote_marker_unresolved` | `warning` | Inline marker cannot be resolved confidently | owner id only; marker allowed if short | warning +1 | yes |
| `footnote_owner_uncertain` | `warning` | Footnote cannot be assigned to chapter/section confidently | internal footnote id only | warning +1 | yes |
| `footnote_duplicate_marker` | `warning` | Duplicate markers are ambiguous in one owner | owner id and marker only | warning +1 | yes |
| `page_number_removed` | `info` | Page number artifact is removed | no text preview | none | yes |
| `repeated_header_footer_removed` | `info` | Repeated running header/footer is removed | no text preview | none | yes |
| `navigation_boilerplate_removed` | `info` | Navigation boilerplate is removed | no URL/path | none | yes |
| `artifact_removed` | `info` | Decorative or layout artifact is removed | no text preview | none | yes |
| `unicode_normalized` | `info` | Text was normalized or mojibake was repaired | no text preview | none | yes |
| `unicode_normalization_failed` | `warning` | Text normalization/repair partially failed | owner id only | warning +1 | yes |
| `html_document_too_large_skipped` | `warning` | One HTML document exceeds `max_html_document_size_bytes` | relative EPUB path or deterministic item id only | warning +1 | yes |
| `html_document_parse_timeout_skipped` | `warning` | One HTML document exceeds `html_parse_timeout_seconds` | relative EPUB path or deterministic item id only | warning +1 | yes |
| `text_block_too_large_split` | `warning` | One block is split to respect `max_text_block_chars` | owner id only | warning +1 | yes |
| `text_block_too_large_dropped` | `warning` | One block cannot be split safely and is dropped | owner id only | warning +1 | yes |
| `empty_readable_content` | `error` | Extraction reaches content analysis but no readable content remains | no text preview | error +1 | no |
| `quality_warning` | `warning` | Generic deterministic quality warning or diagnostic truncation | safe internal id/count only | warning +1 | yes |

Deterministic ordering key:

1. pipeline event order;
2. reading order;
3. affected internal id or relative EPUB path;
4. diagnostic code.

### 18.2 Diagnostic severity invariant

Each diagnostic code has exactly one valid severity in v3.0.

A production result is invalid if any diagnostic uses a severity different from the Diagnostic code matrix. Human-readable diagnostic `message` remains non-stable API.

This invariant MUST be enforced by the official result JSON Schema and by contract tests. A release is invalid when:

- a documented diagnostic code is missing from the schema;
- the schema allows an undocumented diagnostic code;
- the schema allows a `(code, severity)` pair not listed in the matrix;
- production code emits a diagnostic code not documented in the matrix.


### 18.3 Machine-readable diagnostic and error registries

The Markdown matrices in Sections 18 and 19 are human-readable views of normative registry artifacts. The JSON registry files under `schema/` are normative for drift checks, generated tests, and release validation.

Normative registry files:

```text
schema/epub_content_extractor_diagnostic_registry.v3.0.json
schema/epub_content_extractor_error_registry.v3.0.json
```

Each diagnostic registry entry MUST contain:

```json
{
  "code": "metadata_missing_title",
  "severity": "warning",
  "when_emitted": "No usable title metadata is available.",
  "affected_entity_policy": "Do not include raw metadata value.",
  "count_impact": "warning +1",
  "can_appear_in_success": true,
  "message_stability": "not_stable",
  "coverage_status": "integration_fixture",
  "coverage_test_ids": ["TC-019"]
}
```

Allowed `coverage_status` values:

```text
integration_fixture
unit_fixture
fault_injection
schema_only
reserved_not_emitted_by_default
requires_contract_decision
```

Each fatal error registry entry MUST contain:

```json
{
  "code": "input_not_epub",
  "recoverable": false,
  "result_status": "failed",
  "library_behavior": "structured_failed_result",
  "cli_exit_code": 1,
  "cli_json_emission": "yes",
  "when_emitted": "File cannot be opened as a ZIP-based EPUB container.",
  "coverage_status": "integration_fixture",
  "coverage_test_ids": ["TC-013"]
}
```

CI MUST fail if:

- a code appears in the result schema but not the corresponding registry;
- a code appears in a registry but not the result schema;
- a diagnostic code/severity pair differs between registry, schema, and the Markdown matrix;
- an error code's CLI exit mapping differs between the error registry and Section 19.1;
- any release-candidate registry entry has `coverage_status = "requires_contract_decision"`;
- any registry entry has empty `coverage_test_ids` unless `coverage_status` is `reserved_not_emitted_by_default`;
- any registry contains duplicate entries with the same `code`;
- any registry JSON file fails its registry schema.

---

## 19. Error object

```typescript
interface EpubExtractionError {
  code: EpubExtractionErrorCode;
  message: string;
  recoverable: boolean;
}
```

```typescript
type EpubExtractionErrorCode =
  | "invalid_config"
  | "input_file_not_found"
  | "input_not_file"
  | "input_not_epub"
  | "epub_file_too_large"
  | "epub_open_failed"
  | "epub_manifest_unreadable"
  | "epub_archive_security_violation"
  | "no_readable_content"
  | "pipeline_timeout"
  | "output_write_failed"
  | "internal_error";
```

Rules:

- Invalid input file path is fatal.
- Non-EPUB input is fatal.
- EPUB open failure is fatal.
- EPUB archive security violation is fatal.
- EPUB without any readable book content is fatal: `status = "failed"`, `error.code = "no_readable_content"`.
- EPUB without metadata is not fatal.
- EPUB without TOC is not fatal.
- EPUB with missing language metadata is not fatal because output language is fixed to `"en"`.
- `recoverable` MUST be `false` for every `EpubExtractionErrorCode` in v3.0. The field is reserved for future versions and remains stable in shape.
- `output_write_failed` is a reserved structured error code for future/internal output-writer integrations that construct a result object before attempting output persistence. The canonical CLI usually cannot serialize this code to the selected output channel when the output channel itself failed. The canonical `extract_epub_content()` library function MUST NOT return `output_write_failed`, because it does not persist output.
- Error messages are human-readable and are not stable API. `code`, `recoverable`, status, CLI exit mapping, and JSON emission policy are stable API.

### 19.1 Error code matrix

Each fatal extraction failure MUST map to exactly one `EpubExtractionErrorCode`.

| Error code | When emitted | Recoverable | Result status | CLI exit code | JSON emitted by CLI |
|---|---|---:|---|---:|---|
| `invalid_config` | Config file cannot be parsed as JSON or config fails schema validation | false | failed | 4 | yes, if selected output channel is available |
| `input_file_not_found` | `input_path` does not exist, including broken symlink | false | failed | 1 | yes |
| `input_not_file` | `input_path` exists but is not a regular local file | false | failed | 1 | yes |
| `input_not_epub` | File cannot be opened as a ZIP-based EPUB container | false | failed | 1 | yes |
| `epub_file_too_large` | Input file bytes exceed `max_epub_size_bytes` | false | failed | 1 | yes |
| `epub_open_failed` | File appears to be accessible but EPUB container cannot be read after path/size checks, including permission/read errors | false | failed | 1 | yes |
| `epub_manifest_unreadable` | ZIP container opens but EPUB package/OPF manifest cannot be located or parsed | false | failed | 1 | yes |
| `epub_archive_security_violation` | Archive safety policy fails: path traversal, absolute internal path, excessive entries, excessive uncompressed bytes, excessive compression ratio, malformed central directory, or forbidden external resolution attempt | false | failed | 1 | yes |
| `no_readable_content` | Extraction completes or all readable candidates are skipped/dropped/timed out and no readable content remains | false | failed | 1 | yes |
| `pipeline_timeout` | Whole extraction exceeds `pipeline_timeout_seconds` | false | failed | 1 | yes, if result construction is possible |
| `output_write_failed` | Selected CLI output destination cannot be written | false | failed | 3 | no, if selected output channel is unavailable |
| `internal_error` | Unexpected implementation defect | false | failed | 99 | yes, only if result construction and selected output channel are available |

### 19.2 Error and diagnostic interaction

Rules:

- A top-level `error` is required for every structured failed result.
- A diagnostic is not required for early fatal failures when it would duplicate the top-level error.
- If a diagnostic is emitted for the same semantic failure as the top-level error, it MUST use the documented diagnostic code and count policy.
- `output_write_failed` is normally CLI-only and may be impossible to serialize to the selected output channel. Library mode MAY return it only from APIs that explicitly write output; the canonical `extract_epub_content()` library function MUST NOT emit `output_write_failed`.

---

## 20. Processing architecture

The internal architecture remains block-based, but these internals must not leak into the main output schema.

Pipeline:

```text
Raw EPUB
  → EPUB open / metadata read
  → HTML Parsing
  → Block Extraction
  → Feature Extraction
  → Scoring
  → Classification
  → Section / Chapter Structuring
  → Footnote Extraction
  → Post-processing
  → EpubBook object
```

Runtime layer:

```text
ebooklib        → EPUB reading
BeautifulSoup   → HTML parsing
lxml            → parser backend
regex           → cleanup and marker detection
ftfy            → Unicode/text repair
```

### 20.1 Python package, supported versions, and dependency policy

Normative package naming:

- import package: `epub_content_extractor`;
- library entry point: `epub_content_extractor.extract_epub_content`;
- canonical text builder: `epub_content_extractor.build_canonical_text`;
- CLI executable: `epub-content-extractor`.

Supported runtime:

- Python `>=3.11,<3.14` for v3.0.
- The implementation MUST run on Linux, macOS, and Windows when dependencies are available.

Dependency policy:

- `ebooklib`, `beautifulsoup4`, `lxml`, `regex`, `ftfy`, and `jsonschema` are production dependencies in v3.0, not optional output-changing enhancements.
- Dependency major/minor versions MUST be pinned in lockfiles for reproducible fixture outputs and release validation. Patch versions SHOULD also be pinned unless the project uses a controlled update process with fixture regeneration.
- A missing production dependency is an installation/runtime defect and maps to `internal_error` if a structured result can be constructed.
- Parser fallback is allowed only when it does not change production output for contract fixtures. If fallback changes output, it must be treated as a versioned implementation change and covered by regression tests.

Formal layer:

```text
Coq specification may describe:
- data model invariants;
- filtering rules;
- scoring constraints;
- quality invariants.
```

The Coq layer is a specification aid. Python remains the runtime implementation.

---

## 21. Block extraction rules

The internal extractor should consider meaningful text from these tags:

```text
p, div, span, blockquote, h1, h2, h3, h4, h5, h6, li, pre
```

Rules:

- `script`, `style`, `svg`, `noscript`, and hidden navigation boilerplate must be ignored.
- Headings may become chapter or section titles.
- Heading text must not be duplicated into `chapter.text` or `section.text`.
- `li` elements should become independent paragraphs when meaningful.
- Inline spans should be merged into their parent text when they are not standalone semantic blocks.
- Block extraction internals must remain outside the main output schema.

---

## 22. Scoring and filtering internals

Scoring is an internal implementation detail, not part of the main output schema.

Internal formula:

```text
final_score = base_score - penalty + boost
```

Recommended defaults:

```text
base_score = 0.5
```

Penalties:

```text
alpha_ratio < 0.6             → penalty += 0.7
digit_ratio > 0.3             → penalty += 0.5
uppercase short metadata      → penalty += 0.4
length_chars < 25             → penalty += 0.3
navigation-like block         → penalty += 0.6
page-number-like block        → penalty += 0.8
```

Boosts:

```text
has_dialogue_markers          → boost += 0.2
strong prose context          → boost += 0.2
valid chapter heading context → boost += 0.3
```

Classification:

```text
final_score < 0       → drop
final_score < 0.3     → maybe
final_score >= 0.3    → keep
```

Production thresholds:

```text
MIN_CHARS = 25
MIN_ALPHA_RATIO = 0.6
MAX_DIGIT_RATIO = 0.3
KEEP_SCORE = 0.3
```

Rules:

- These values are implementation defaults, not output fields.
- Changing them requires regression testing.
- Main output must not expose block scores unless debug mode is enabled.

---

## 23. Uppercase metadata vs valid short chapter titles

Uppercase short blocks should not be blindly dropped.

A short uppercase block may be treated as a valid title when at least one condition is true:

- it appears in TOC as a chapter/section title;
- it is a strong heading tag (`h1`, `h2`, `h3`);
- it is followed by a dense prose block cluster;
- it matches common literary structure labels such as `ACT I`, `SCENE I`, `CHAPTER I`, `PART ONE`;
- it appears at a chapter boundary.

Otherwise, it may be treated as uppercase metadata or noise.

---

## 24. Section skipping

Section skipping removes or excludes content that is not useful for canonical downstream text.

Rules:

- Copyright sections should be preserved structurally when detected but excluded from canonical text.
- Advertisements should be preserved structurally when meaningful but excluded from canonical text.
- Publisher notes should be preserved structurally when meaningful but excluded from canonical text.
- TOC text should be preserved as `table_of_contents` but excluded from canonical text.
- Navigation boilerplate should be removed completely.
- Page numbers should be removed completely.
- Repeated headers and footers should be removed completely.

---

## 25. Density clustering

Density clustering is an internal method for distinguishing prose regions from navigation/noise regions.

Recommended approach:

- Group neighboring blocks inside a section.
- Estimate text density using alpha ratio, average block length, punctuation ratio, and paragraph continuity.
- Treat dense clusters of readable prose as primary content.
- Treat sparse clusters of short links, numbers, headings, or navigation as non-content unless they are validated as titles.

Density clustering may influence extraction but must not appear in the main output schema.

---

## 26. Neighbor validation

Neighbor validation is an internal method for preserving weak blocks that are likely part of surrounding prose.

Rule:

```text
A weak block may be kept if it is surrounded by strong prose blocks in the same logical section.
```

Typical use cases:

- short dialogue lines;
- short dramatic stage directions;
- short continuation paragraphs;
- one-line list items in a meaningful list.

Neighbor validation may influence extraction but must not appear in the main output schema.

---

## 27. Footnote detection internals

Footnote detection must happen before final text assembly.

Pipeline:

```text
1. Detect footnote/endnote blocks.
2. Build marker → footnote index.
3. Detect inline markers in paragraphs.
4. Resolve inline marker to footnote when confidence is high.
5. Remove resolved inline marker from paragraph text.
6. Preserve unresolved inline marker and emit diagnostic.
7. Assign footnote to chapter/section/book level.
```

Recommended confidence rule:

```text
inline_confidence > 0.6 → remove marker
otherwise               → keep marker
```

Confidence signals:

- marker text matches a detected footnote marker;
- marker appears near expected paragraph context;
- target footnote is in same chapter/section;
- target marker is unique;
- marker style is compatible with footnote-like markup.

---

## 28. Unicode normalization and artifacts

Unicode normalization is mandatory best-effort processing.

Rules:

- All emitted production text fields MUST be normalized to Unicode NFC after text cleanup and optional mojibake repair.
- Character counts are computed after final NFC normalization.
- Mojibake repair is best-effort and MUST NOT replace valid text with lower-confidence guesses.
- If repair fails, keep the best available text, normalize to NFC when possible, and emit diagnostic `unicode_normalization_failed`.
- Normalize repeated whitespace.
- Preserve meaningful punctuation.
- Do not remove apostrophes, quotation marks, em dashes, or dialogue punctuation.
- If normalization partially fails, keep the best available text and emit diagnostic `unicode_normalization_failed`.

Common removable artifacts:

```text
page numbers
repeated running headers
repeated running footers
navigation arrows
isolated bullets with no text
isolated decorative separators
publisher navigation labels
empty anchors
```

---

## 29. Quality guarantees

The extractor should protect these quality invariants:

```text
no_word_gluing
sentence_integrity
readability
```

Meaning:

- `no_word_gluing`: words should not be accidentally joined during tag removal or paragraph merge.
- `sentence_integrity`: sentence endings and punctuation should not be systematically destroyed.
- `readability`: canonical text should be human-readable and should not be dominated by navigation, metadata, or artifacts.

These checks may be implemented as tests, assertions, diagnostics, or property-based tests.

---

## 30. Limits and timeout defaults

Recommended defaults:

```text
MAX_EPUB_SIZE_BYTES = 100 MB = 104857600 bytes
MAX_HTML_DOCUMENT_SIZE_BYTES = 10 MB = 10485760 bytes
MAX_TEXT_BLOCK_CHARS = 100_000 Unicode code points
PIPELINE_TIMEOUT_SECONDS = 120
HTML_PARSE_TIMEOUT_SECONDS = 20
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 500 MB = 524288000 bytes
MAX_ARCHIVE_ENTRY_COUNT = 10000
MAX_ARCHIVE_COMPRESSION_RATIO = 100
MAX_TOC_DEPTH = 8
MAX_DIAGNOSTIC_COUNT = 1000
MAX_OUTPUT_JSON_BYTES = 500 MB = 524288000 bytes
```

Rules:

- Limits must be configurable through `EpubContentExtractorConfig`.
- Configurable limits are bounded by the hard maximums defined in the config schema.
- All byte and character limits are inclusive.
- A value is allowed when `actual <= configured_limit`.
- A value exceeds the limit when `actual > configured_limit`.
- `MAX_EPUB_SIZE_BYTES` is measured in file bytes before EPUB parsing.
- `MAX_HTML_DOCUMENT_SIZE_BYTES` is measured in uncompressed HTML document bytes before parsing that HTML document.
- `MAX_TEXT_BLOCK_CHARS` is measured in Unicode code points after text extraction and Unicode normalization.
- `MAX_OUTPUT_JSON_BYTES` is measured as UTF-8 bytes of the exact JSON representation that would be written by the selected output mode.
- Exceeding EPUB size limit is fatal: `error.code = "epub_file_too_large"`.
- Exceeding whole-pipeline timeout is fatal: `error.code = "pipeline_timeout"`.

### 30.1 Oversized individual HTML documents

Policy: skip.

Rules:

- If an individual HTML document has `size_bytes > max_html_document_size_bytes`, the extractor must skip that HTML document.
- The extractor must not truncate oversized HTML documents.
- The extractor must not parse oversized HTML documents partially in normal mode.
- Skipping one oversized HTML document is non-fatal if enough readable content remains elsewhere.
- Each skipped oversized HTML document must emit diagnostic `html_document_too_large_skipped` with severity `warning`.
- If all readable content is skipped or absent, the final result must fail with `error.code = "no_readable_content"` and include relevant diagnostics.

### 30.2 HTML document parse timeout policy

If parsing one HTML document exceeds `html_parse_timeout_seconds`, the extractor MUST stop parsing that HTML document and skip it.

Rules:

- A per-document parse timeout is non-fatal if enough readable content remains elsewhere.
- The extractor MUST emit diagnostic `html_document_parse_timeout_skipped` with severity `warning`.
- The extractor MUST NOT emit partial content from the timed-out HTML document in normal mode.
- If all readable content is absent, skipped, dropped, or timed out, the final result MUST fail with `error.code = "no_readable_content"`.
- Whole-pipeline timeout still fails extraction with `error.code = "pipeline_timeout"`.

### 30.3 Oversized individual text blocks

Policy: split when safe, otherwise drop. Never silently truncate.

Rules:

- If a text block has `chars <= max_text_block_chars`, keep normal processing.
- If a text block has `chars > max_text_block_chars`, first attempt deterministic splitting at structural or safe textual boundaries.
- Safe split boundaries are paragraph-like block boundaries, list item boundaries, sentence boundaries, or whitespace boundaries that do not glue words.
- Every emitted split fragment must have `chars <= max_text_block_chars`.
- When a block is split because of this limit, emit `text_block_too_large_split` with severity `warning`.
- If the block cannot be split safely, drop the block and emit `text_block_too_large_dropped` with severity `warning`.
- The extractor must not truncate oversized text blocks in normal mode.
- Dropped oversized text blocks contribute to `removed_section_count` only when the dropped block corresponds to a whole removed section; otherwise they are excluded from text and paragraph counts.

### 30.4 EPUB archive safety policy

The extractor MUST treat EPUB files as untrusted ZIP-based archives.

Rules:

- The extractor MUST NOT perform network calls while processing EPUB content.
- The extractor MUST NOT resolve external URLs referenced from HTML, CSS, metadata, manifest items, SVG, or scripts. External references are ignored as resources and are not fatal unless an implementation attempts forbidden external resolution.
- Archive safety checks MUST run immediately after ZIP open and before OPF/package discovery, XML parsing, HTML parsing, asset inspection, or manifest item processing.
- The extractor MUST validate ZIP central directory consistency before trusting entry metadata.
- Encrypted ZIP entries are unsupported in v3.0 and MUST fail with `epub_archive_security_violation`.
- The extractor MUST normalize every archive entry path using POSIX-style EPUB archive semantics before use.
- The extractor MUST reject archive entries whose normalized path escapes the EPUB container root.
- Absolute paths, drive-letter paths, UNC paths, backslash-based traversal, and `..` path traversal are invalid.
- ZIP entries that represent symlinks or platform-specific link-like filesystem objects are invalid and MUST fail with `epub_archive_security_violation`.
- The extractor MUST enforce `max_archive_entry_count` before parsing content.
- The extractor MUST enforce `max_archive_uncompressed_bytes` across all archive entries before parsing content.
- The extractor MUST enforce `max_archive_compression_ratio` using the formula below.
- Malformed ZIP central directory data MUST fail deterministically.
- XML entity expansion and external entity resolution MUST be disabled before parsing any XML, XHTML, HTML, NCX, OPF, or SVG-like content.
- SVG content is ignored as readable content and treated as opaque asset metadata unless a future version defines safe SVG metadata extraction.
- Archive safety failures map to `error.code = "epub_archive_security_violation"`.

Archive safety precedence after ZIP open:

1. Validate ZIP central directory consistency.
2. Reject encrypted entries.
3. Normalize and validate every archive entry path.
4. Reject symlink/link-like entries.
5. Enforce `max_archive_entry_count`.
6. Enforce aggregate `max_archive_uncompressed_bytes`.
7. Enforce per-entry and aggregate `max_archive_compression_ratio`.
8. Configure XML/HTML parsers with external entity resolution disabled.
9. Only after these checks, locate and parse the EPUB package/OPF document.

Compression ratio formula:

```text
entry_compression_ratio = entry_uncompressed_size / max(entry_compressed_size, 1)
aggregate_compression_ratio = total_uncompressed_size / max(total_compressed_size, 1)
```

Rules:

- Both per-entry and aggregate ratios MUST be enforced.
- A ratio is allowed when `ratio <= max_archive_compression_ratio`.
- A ratio exceeds the limit when `ratio > max_archive_compression_ratio`.
- Directory entries with zero uncompressed bytes do not fail ratio checks by themselves, but still count toward entry count.
- If both archive security failure and missing/unreadable manifest are true, `epub_archive_security_violation` takes precedence.

Limit behavior:

| Limit | Default | Behavior when exceeded |
|---|---:|---|
| `max_archive_uncompressed_bytes` | `524288000` | fatal `epub_archive_security_violation` |
| `max_archive_entry_count` | `10000` | fatal `epub_archive_security_violation` |
| `max_archive_compression_ratio` | `100` | fatal `epub_archive_security_violation` |
| `allow_network_access` | `false` | fixed, not configurable |

---

## 31. Determinism

The extractor must be deterministic for the same:

- input file bytes;
- extractor version;
- config;
- dependency versions.

Rules:

- Output ordering must be stable.
- Author order should follow EPUB metadata order when available.
- Chapter order must follow reading order.
- Internal ids must be generated deterministically.
- Current timestamps in `extraction.started_at` / `finished_at` are allowed to differ between runs.

### 31.1 JSON serialization order

For CLI output, JSON object keys MUST be emitted in schema order as documented in `schema/epub_content_extractor.v3.0.schema.json`.

Rules:

- Consumers SHOULD compare parsed JSON semantically rather than relying on key order.
- Array ordering remains semantically significant and MUST be deterministic.
- `--pretty` and compact output MUST parse to identical objects.
- Timestamp precision is seconds by default. Fractional seconds MUST NOT be emitted in v3.0 examples or contract fixtures unless the result schema is updated to require them.
- `started_at` and `finished_at` MUST be UTC RFC-3339 strings ending with `Z`.

---

## 32. Logging and privacy

Diagnostics are part of the structured result and may be logged by higher-level systems.

The extractor itself must avoid logging sensitive or excessive data.

Forbidden in logs by default:

- full extracted book text;
- full paragraph text;
- full local absolute input path;
- raw HTML content;
- binary asset data;
- large metadata blobs;
- user-specific filesystem structure.

Allowed in logs:

- error code;
- diagnostic code;
- counts and durations;
- input file name only;
- input file size;
- SHA-256 hash when needed for reproducibility.

---

## 33. Debug mode

Debug mode is optional and must be disabled by default.

When effective config `include_debug = true`, debug data is placed in the top-level result field named `debug`.

```typescript
interface EpubDebugInfo {
  manifest?: unknown[];
  spine?: unknown[];
  raw_blocks?: unknown[];
  scoring?: unknown[];
  source_maps?: unknown[];
  parser?: unknown;
  timings?: unknown;
  redaction?: {
    applied: boolean;
    text_preview_max_chars: number;
    html_preview_max_chars: number;
  };
}
```

Rules:

- The only allowed top-level field name for debug data is `debug`.
- `debug_info`, `_debug`, and `debugData` must not be used.
- Debug data is not part of the normal production output contract.
- Debug data may contain implementation-specific structures.
- Debug data must not be required by downstream modules.
- Debug data should not be logged in production.
- `include_debug = true` must not change extraction semantics, diagnostics, counts, or canonical text.
- If effective `extraction.config.include_debug = false`, top-level `debug` MUST be absent.
- If effective `extraction.config.include_debug = true`, top-level `debug` MAY be present but is not required.
- The official result schema MUST reject a result that contains top-level `debug` while `extraction.config.include_debug = false`.

Sensitive data policy for debug mode:

- Debug mode may include file names, manifest item ids, spine ids, media types, href-like relative EPUB paths, parser timings, block classifications, scores, and deterministic internal ids.
- Debug mode must not include absolute local filesystem paths.
- Debug mode must not include binary asset data.
- Debug mode must not include full raw HTML documents.
- Debug mode must not include full book text or full paragraph text.
- Debug mode may include short redacted previews for troubleshooting:
  - `text_preview` up to 200 Unicode code points;
  - `html_preview` up to 500 Unicode code points.
- Previews must be trimmed, must not include surrounding local filesystem context, and may be omitted even when `include_debug = true`.
- If redaction is applied, `debug.redaction.applied` MUST be `true`.

### 33.1 Debug preview redaction policy

Debug previews are optional even when `include_debug = true`.

Rules:

- Implementations MAY omit all `text_preview` and `html_preview` fields.
- If previews are emitted, they MUST be redacted before truncation.
- Previews MUST be omitted or redacted when they match deterministic sensitive patterns, including:
  - email addresses;
  - access tokens and API keys using common prefixes or high-entropy token-like strings;
  - PEM/private-key blocks;
  - absolute local paths;
  - URLs with credentials;
  - long digit sequences of 9 or more digits that look like identifiers;
  - credit-card-like digit groupings;
  - environment-variable assignments containing `TOKEN`, `SECRET`, `PASSWORD`, `KEY`, or `CREDENTIAL`.
- Redaction replacement text MUST be deterministic, for example `[REDACTED_EMAIL]`.
- `debug.redaction.applied` MUST be `true` if any preview was omitted or modified for privacy.
- Debug mode MUST NOT change production fields, diagnostics, counts, or canonical text.

---

## 34. Property-based testing, schema validation, and Coq specification

Property-based tests are recommended for v3.0 quality assurance.

Recommended properties:

```text
chapter.text is present and non-empty for every emitted chapter
no chapters[].paragraphs field exists in production output
section.text == join(section.paragraphs[].text, "

")
book.language == "en"
no book-level text field exists
all chapter ids are unique
all section ids are unique
all footnote ids are unique
all TOC target_ids resolve or are omitted
build_canonical_text is deterministic
resolved inline footnote markers are removed
unresolved inline footnote markers are preserved
all emitted successful results validate against schema/epub_content_extractor.v3.0.schema.json
all emitted failed results validate against schema/epub_content_extractor.v3.0.schema.json when a JSON result is emitted
succeeded results contain at least one chapter with non-empty text or one front_matter/back_matter section with non-empty text and at least one paragraph
succeeded results contain no diagnostics with severity == error
debug is absent when extraction.config.include_debug == false
every diagnostic code uses the severity defined in the diagnostic matrix
all accepted configs validate against schema/epub_content_extractor_config.v3.0.schema.json
invalid configs produce error.code == "invalid_config"
invalid config result uses default extraction.config snapshot
warning_count matches emitted warning diagnostics
error_count matches documented top-level-error formula
all production text fields are NFC-normalized
successful local extraction emits source_file.sha256
archive path traversal fails with epub_archive_security_violation
archive path traversal plus missing OPF still fails with epub_archive_security_violation
archive zip bomb limits fail before content parsing
encrypted ZIP entries fail with epub_archive_security_violation
per-HTML parse timeout emits html_document_parse_timeout_skipped or no_readable_content if all content times out
CLI compact and pretty output parse to identical objects
CLI object key order follows schema order
```

Runtime validation policy:

- Production runtime validation of every emitted result against JSON Schema is optional and disabled by default.
- CI and release tests must validate fixture outputs against the official result schema.
- Unit tests must validate config parsing against the official config schema.
- A development or test-only runtime validation flag may be added, but it must not change production semantics.

### 34.1 Fixture and golden output policy

Contract tests MUST NOT commit generated binary EPUB or ZIP fixtures as source artifacts. Binary EPUB/ZIP inputs are generated at test runtime under the test temporary directory from deterministic committed fixture source specs.

Required repository-root layout for each executable contract fixture:

```text
tests/fixtures/epub_content_extractor/<category>/<fixture_id>/fixture.json
tests/fixtures/epub_content_extractor/<category>/<fixture_id>/config.json
tests/fixtures/epub_content_extractor/<category>/<fixture_id>/expected.normalized.json
```

All golden manifest paths are repository-root-relative. The golden acceptance manifest MUST declare `path_base = "repo_root"`, and release validation MUST resolve paths against the explicit `--repo-root` argument rather than the process current working directory.

`fixture.json` describes how to generate the runtime input file and MUST validate against:

```text
schema/epub_content_extractor_fixture_manifest.v3.0.schema.json
```

`fixture.json.generator.source_spec` MUST be a machine-readable object, not a prose placeholder. It must include deterministic generation details such as format, ZIP entry order, ZIP timestamp, compression method, and exact source entries or inline object data.

`expected.normalized.json` is compared after applying `normalize_result_for_snapshot()` from the testing guide. The normalizer may replace only:

- `extraction.started_at`;
- `extraction.finished_at`;
- `extraction.duration_ms`.

Generated binary EPUB/ZIP files MUST be written only under the test temporary directory and MUST NOT be committed to the repository.

Rules:

- Golden outputs MUST validate directly against the official result schema after schema-preserving timestamp/duration normalization. The snapshot normalizer MUST use valid sentinel timestamps rather than non-schema placeholder strings.
- CLI stderr snapshots are stable only for exit code, safe category, and absence of sensitive data; exact prose is not stable API.
- There MUST be at least one fixture or documented coverage status for every fatal error code and every diagnostic code that production code may emit.
- Diagnostic codes with `coverage_status = "reserved_not_emitted_by_default"` are schema-reserved in v3.0. Production code MUST NOT emit them unless the registry entry is changed to `integration_fixture`, `unit_fixture`, or `fault_injection` in a future contract version.
- The diagnostic registry schema intentionally permits `coverage_status = "requires_contract_decision"` so draft registries can validate structurally.
- Release-candidate registries MUST NOT contain `coverage_status = "requires_contract_decision"`. Release validation MUST run the additional semantic check that rejects this draft-only value in normative release registry files.
- There MUST be explicit fixtures for wrong diagnostic severity rejection, no-readable-content success rejection, debug-when-disabled rejection, `$schema` input config acceptance, and unknown config field rejection.
- There MUST be boundary fixtures for every inclusive limit at `actual == limit` and `actual == limit + 1` where practical.

### 34.3 Release documentation validation command

The repository MUST expose a release validation command:

```bash
python -m epub_content_extractor_contracts.validate_release_docs --repo-root .
```

The command MUST fail on schema/registry drift, unresolved `schema/` aliases, invalid or incomplete test coverage manifests, any P0 test with `blocking_status != "ready"`, fixture ID mismatch, missing golden paths, fixture manifests that are not executable source specs, successful goldens containing `chapters[].paragraphs`, invalid normalized timestamps, and canonical prose/source/config/golden disagreement for committed fixtures.

When invoked with `--json`, the command MUST emit a machine-readable summary containing `status`, `error_count`, `warning_count`, and stable failed-check IDs.

### 34.2 Heuristic acceptance fixture matrix

Chapter, section, TOC, and readable-content heuristics are implementation details, but fixture outcomes are normative for v3.0 release validation.

The fixture suite MUST include representative EPUBs for:

- TOC-driven chapters with resolved targets;
- missing TOC with spine-order fallback;
- one HTML spine document split by multiple strong headings;
- uppercase valid short titles such as `ACT I`, `SCENE I`, and `PART ONE`;
- uppercase metadata/noise that must not become chapter titles;
- dense prose block clusters that preserve weak neighboring blocks;
- front matter and back matter detection;
- advertisement, copyright, publisher notes, bibliography, and index exclusion from canonical text;
- unresolved TOC targets;
- footnote ownership confidence and duplicate marker ambiguity.

For each heuristic fixture, expected output MUST define the stable externally visible result: chapter/section boundaries, ids, types, titles, text, diagnostics, and summary counts. Implementations may use different internal scoring only if they produce the same fixture outputs.

Coq specification may be used to define invariants and generate tests, but runtime support for Coq is not required.

---

## 35. Example successful output

```json
{
  "schema_version": "epub_content_extractor.v3.0",
  "status": "succeeded",
  "book": {
    "title": "A Doll's House",
    "subtitle": null,
    "language": "en",
    "authors": [
      {
        "name": "Henrik Ibsen",
        "role": "author"
      }
    ],
    "contributors": [
      {
        "name": "William Archer",
        "role": "translator"
      }
    ],
    "metadata": {
      "identifiers": [
        {
          "scheme": "Project Gutenberg",
          "value": "2542"
        }
      ],
      "publisher": "Project Gutenberg",
      "published_at": null,
      "modified_at": null,
      "description": null,
      "rights": "Public domain",
      "subjects": ["Drama"],
      "source_file": {
        "file_name": "a_dolls_house.epub",
        "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "size_bytes": 1234567,
        "epub_version": "3.0"
      }
    },
    "front_matter": [
      {
        "id": "front_001",
        "type": "title_page",
        "title": "A Doll's House",
        "text": "by Henrik Ibsen",
        "paragraphs": [
          {
            "text": "by Henrik Ibsen"
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
        "type": "act",
        "title": "ACT I",
        "text": "A room furnished comfortably and tastefully.\n\nNora: Hide the Christmas Tree carefully, Helen.",
        "footnotes": []
      }
    ],
    "back_matter": [],
    "footnotes": [],
    "table_of_contents": [
      {
        "title": "ACT I",
        "type": "chapter",
        "target_id": "chapter_001",
        "chapter_number": 1,
        "children": []
      }
    ],
    "assets": []
  },
  "diagnostics": [],
  "extraction": {
    "extractor_version": "3.0.0",
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
      "front_matter_section_count": 1,
      "back_matter_section_count": 0,
      "paragraph_count": 1,
      "footnote_count": 0,
      "total_text_chars": 108,
      "canonical_text_chars": 100,
      "removed_section_count": 0,
      "warning_count": 0,
      "error_count": 0
    }
  }
}
```

---

## 36. Example failed output

```json
{
  "schema_version": "epub_content_extractor.v3.0",
  "status": "failed",
  "error": {
    "code": "input_not_epub",
    "message": "Input file is not a valid EPUB archive.",
    "recoverable": false
  },
  "diagnostics": [],
  "extraction": {
    "extractor_version": "3.0.0",
    "started_at": "2026-05-08T10:00:00Z",
    "finished_at": "2026-05-08T10:00:00Z",
    "duration_ms": 12,
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
  }
}
```

---

## 37. Compatibility and versioning policy

The extractor uses SemVer for the implementation package and explicit schema versions for output/config contracts.

Rules:

- `extractor_version` follows SemVer 2.0.0.
- `schema_version` identifies the result schema contract and is not automatically equal to `extractor_version`.
- Config schema `$id` identifies the config validation contract.
- Patch releases MUST NOT intentionally change successful production output for existing fixtures, except for bug fixes that are explicitly documented and covered by updated fixtures.
- Minor releases MAY add optional fields, diagnostic codes, error codes, config fields, or debug fields when backward-compatible for consumers that ignore unknown future schema versions.
- Major releases MAY remove or rename fields, change required fields, change existing enum semantics, or alter public Python signatures.

The following are breaking changes and require at least a new schema version, and usually a major implementation version when public APIs are affected:

- changing `schema_version` semantics or result top-level shape;
- removing, renaming, or changing the type/nullability of any production field;
- changing required/optional field presence;
- changing an existing diagnostic code's severity;
- removing or renaming a diagnostic or error code;
- changing CLI exit-code meaning;
- changing CLI stdout/stderr machine-readable behavior;
- changing `extract_epub_content()` or `build_canonical_text()` public signatures;
- changing config field names, types, defaults, minimums, or maximums;
- allowing debug data to affect production fields.

The following are non-breaking within the same schema version when fixture outputs remain valid:

- improving internal heuristics without changing contract fixture outputs;
- changing diagnostic human-readable `message` prose;
- adding implementation-specific debug subfields when `include_debug = true`;
- performance improvements;
- internal refactoring.

`output_json_too_large` is intentionally not added to v3.0 to avoid changing the error enum in-place. A future schema version SHOULD add it and map serialized-output-size overflow to that dedicated code instead of `internal_error`.

---

## 38. Resolved decisions

The following decisions are fixed in v3.0:

1. Output is a structured object, not plain text.
2. The module is library + CLI only.
3. `EpubBook` does not contain a full `text` field.
4. Language is always `"en"`.
5. No language detection is required.
6. Text is stored only in chapters, sections, and footnotes.
7. Canonical downstream text is produced by `build_canonical_text(book, options)`.
8. `chapter.text` does not include `chapter.title`.
9. `section.text` does not include `section.title`.
10. `chapter.text` is the authoritative public chapter body field; `chapters[].paragraphs` is not part of the production schema.
11. `section.text` is derived from `section.paragraphs[].text`.
12. Footnote text is not included in chapter/section text by default.
13. Resolved inline footnote markers are removed.
14. Unresolved inline footnote markers are preserved.
15. Front matter and back matter are preserved structurally.
16. Copyright, ads, publisher notes, bibliography, and index are excluded from canonical text by default.
17. Navigation boilerplate, page numbers, repeated headers/footers, and layout artifacts may be removed completely.
18. `sentences[]` are not part of v3.0 output.
19. `sentence_count` and `has_dialogue` are not part of the main schema.
20. Chapters, sections, and footnotes have internal stable ids.
21. Chapter type supports `chapter`, `part`, `act`, `scene`, `section`, and `unknown`.
22. Images are not extracted as binary data; only lightweight asset metadata may be emitted.
23. EPUB without readable content is a failed extraction.
24. EPUB without metadata can still be a successful extraction.
25. Scoring, source maps, raw blocks, and density clusters are debug-only implementation details.
26. The official config schema is `schema/epub_content_extractor_config.v3.0.schema.json`.
27. The official result schema is `schema/epub_content_extractor.v3.0.schema.json`.
28. Invalid config in library mode returns `status = "failed"` with `error.code = "invalid_config"`.
29. CLI usage errors exit `2` and emit only human-readable stderr, not JSON.
30. CLI invalid config exits `4` and emits JSON failed result when the selected output channel is available.
31. CLI output write failure exits `3` and does not emit JSON fallback to stdout when `--output` was requested.
32. All byte and character limits are inclusive: `actual <= limit` is allowed; `actual > limit` exceeds.
33. Oversized individual HTML documents are skipped and emit `html_document_too_large_skipped`.
34. Oversized individual text blocks are split when safe, otherwise dropped; they are never silently truncated.
35. Debug data is emitted only as top-level `debug` and only when `include_debug = true`.
36. Diagnostics have stable deterministic ordering.
37. `metadata_missing_title` is `warning`.
38. `metadata_language_conflicts_with_contract` is `warning`.
39. Invalid metadata dates are emitted as `null`, not raw strings.
40. `title` and `subtitle` are emitted as `string | null` in successful results.
41. `extractor_version` must be SemVer-compatible without a leading `v`.
42. Text character counts use Unicode code points, not bytes.
43. `total_text_chars` includes preserved front matter, chapters, and back matter, but excludes footnotes.
44. `paragraph_count` counts only emitted front matter and back matter `EpubParagraph` objects; chapter paragraph-like units are internal.
45. `footnote_count` counts book-level, chapter-level, and section-level footnotes together.
46. Nested TOC children are resolved independently of unresolved parents.
47. Successful `book` arrays are always emitted as arrays; failed results omit `book` entirely.
48. Emitted structured failed results always include `extraction.summary`, `finished_at`, and `duration_ms`.
49. `--version` prints version only and exits `0`.
50. `--help` prints help text and exits `0`.
51. `--pretty` changes formatting only.
52. Human-readable logs are disabled by default for successful extraction.
53. Production runtime schema validation is optional; CI/release schema validation is required.
54. Required nullable fields are emitted with value or `null`; optional fields are omitted when unknown.
55. Invalid config failed results use the default effective config snapshot and never expose raw invalid config in production output.
56. CLI failure precedence is parse → help/version → config → input → extraction → serialize → write.
57. Actual EPUB container validation is required; the `.epub` extension is not sufficient.
58. EPUB archive safety checks are mandatory before content parsing.
59. Network access and external resource fetching are always disabled.
60. Per-document HTML parse timeout skips that document with `html_document_parse_timeout_skipped` and fails only if no readable content remains.
61. `extraction.summary.warning_count` and `error_count` follow the documented diagnostic/top-level-error formula.
62. All emitted production text fields are normalized to Unicode NFC.
63. Successful local extraction emits lowercase hexadecimal `source_file.sha256`.
64. CLI JSON object keys are emitted in schema order.
65. Debug previews are optional; if emitted, deterministic redaction is mandatory.
66. `recoverable` is always `false` for every v3.0 error code.
67. Parent directories for `--output PATH` must already exist.
68. `--output -` means stdout.
69. Production dependencies are fixed for v3.0 and absence of a dependency is an implementation/runtime defect.
70. Input config may contain tooling-only `$schema`; `extraction.config` never contains `$schema`.
71. Diagnostic severity is fixed per diagnostic code and enforced by schema plus contract tests.
72. Successful results must contain at least one readable chapter with non-empty `chapter.text` or one front/back matter section with non-empty text and paragraph output.
73. Archive safety checks run after ZIP open and before OPF/package discovery or parsing.
74. Encrypted ZIP entries, symlink-like ZIP entries, malformed central directories, traversal paths, absolute paths, excessive entries, excessive uncompressed bytes, and excessive compression ratios are archive security violations.
75. Compression ratio is enforced both per-entry and in aggregate using `uncompressed_size / max(compressed_size, 1)`.
76. `extract_epub_content()` returns a plain JSON-compatible `dict[str, object]` result shape for normal extraction outcomes.
77. `build_canonical_text()` invalid inputs are programmer errors and raise `TypeError` or `ValueError`.
78. CLI `--config -` reads config JSON from stdin.
79. CLI `--output PATH` overwrites existing files atomically with same-directory temp file plus replace.
80. Top-level `debug` is forbidden when `extraction.config.include_debug = false`.
81. Config resource limits have hard schema maximums.
82. v3.0 keeps output-size overflow mapped to `internal_error` as a compatibility compromise; a future schema should add `output_json_too_large`.
83. Public `build_canonical_text()` options are partial boolean-only mappings; separator options are internal constants and rejected as public keys.
84. Machine-readable diagnostic and error registries under `schema/` are normative for drift and coverage validation.
85. The `.epub` extension is advisory; content-based EPUB validation determines acceptance or failure.
86. `schema/<file>` is a prose alias for `docs/architecture/schema/<file>` during release validation.
87. `docs/testing/epub_content_extractor_test_coverage_manifest.v3.0.json` is the machine-readable TC-to-fixture/assertion coverage contract.
88. Module-specific architecture and schemas override shared guidelines on conflicts.
86. Removing `chapters[].paragraphs` is an intentional v3.0 breaking schema change; chapter body content is exposed through `chapter.text`.

---

## 39. Main schema summary

```text
EpubContentExtractionResult
  schema_version
  status
  book?
    title: string | null
    subtitle: string | null
    language = "en"
    authors[]
    contributors[]
    metadata
      identifiers[]
      publisher
      published_at
      modified_at
      description
      rights
      subjects[]
      source_file
    front_matter[]
      id
      type
      title
      text
      paragraphs[]
      footnotes[]
      included_in_canonical_text
    chapters[]
      id
      chapter_number
      type
      title
      text
      footnotes[]
    back_matter[]
      id
      type
      title
      text
      paragraphs[]
      footnotes[]
      included_in_canonical_text
    footnotes[]
    table_of_contents[]
    assets[]
  error?
  diagnostics[]
    code
    severity
    message
    entity_type?
    entity_id?
    field?
  extraction
    extractor_version
    started_at
    finished_at
    duration_ms
    config
      include_front_matter_in_canonical_text
      include_back_matter_in_canonical_text
      include_footnotes_in_canonical_text
      include_chapter_titles_in_canonical_text
      include_section_titles_in_canonical_text
      max_epub_size_bytes
      max_html_document_size_bytes
      max_text_block_chars
      pipeline_timeout_seconds
      html_parse_timeout_seconds
      max_archive_uncompressed_bytes
      max_archive_entry_count
      max_archive_compression_ratio
      max_toc_depth
      max_diagnostic_count
      max_output_json_bytes
      include_debug
    summary
  debug?
```


---

## 40. Glossary

| Term | Definition |
|---|---|
| Readable content | Human-readable prose, dialogue, list text, dramatic directions, or semantically meaningful notes that remain after artifact removal and normalization. |
| Content-bearing section | A front matter, chapter, back matter, or footnote container with non-empty final text. Front/back matter sections expose paragraphs; chapters expose only `chapter.text` in production output. |
| Valid and useful TOC | A table of contents whose entries can be ordered and mapped to reading-order content without dominating output with navigation noise. |
| Strong heading | A heading element or heading-like block that is supported by TOC, spine boundary, dense prose context, or known literary structure pattern. |
| High confidence | Deterministic evidence strong enough to change output shape without exposing uncertain assumptions. Numeric implementations use `confidence >= 0.85` unless a section specifies another threshold. |
| Safe split | A split at a structural, sentence, list-item, or whitespace boundary that does not glue words, remove punctuation, or create empty output fragments. |
| Navigation boilerplate | Repeated or low-content links, previous/next labels, page navigation, publisher nav elements, and other text that helps navigate the EPUB but is not book content. |
| Production output | The normal JSON result excluding top-level `debug`. |
| Debug preview | A short, redacted troubleshooting excerpt allowed only inside top-level `debug` when `include_debug = true`. |

---

## 41. v3.0 change log from v2.2

v3.0 is a breaking schema update focused on removing chapter-level paragraph arrays from production output while preserving section paragraph arrays for front/back matter:

- Removed `chapters[].paragraphs` from `EpubChapter` and from the main result schema summary.
- Made `chapter.text` the authoritative public chapter body field.
- Updated readable-content invariants so chapters require non-empty `chapter.text`, while front/back matter sections still require non-empty `paragraphs[]` and `text`.
- Updated canonical text builder rules to use `chapter.text` and `section.text` directly.
- Updated `paragraph_count` semantics to count only emitted `EpubParagraph` objects in front/back matter sections.
- Updated examples, property tests, and resolved decisions to reject `chapters[].paragraphs` in production output.

The following v2.2 review findings remain incorporated in the v3.0 baseline:

- Added mandatory normative result JSON Schema requirement.
- Added global optional vs nullable JSON field policy.
- Defined invalid config failed-result behavior and default config snapshot policy.
- Added deterministic CLI failure precedence.
- Added exact EPUB input validation order and symlink policy.
- Added full error code matrix and `epub_archive_security_violation`.
- Added full diagnostic code matrix and `html_document_parse_timeout_skipped`.
- Added warning/error count formula.
- Added archive security limits and no-network policy.
- Defined per-HTML parse timeout behavior.
- Mapped extractor config to canonical text builder options.
- Required NFC normalization for production text fields.
- Required `source_file.sha256` for successful local extraction.
- Defined CLI JSON key order, timestamp precision, and output directory behavior.
- Added deterministic debug redaction policy.
- Added dependency/version policy, fixture layout, duplicate metadata policy, empty-string policy, TOC depth behavior, and glossary.
- Synchronized config `$schema` tooling policy with the config schema.
- Added hard maximums for configurable resource limits.
- Added result-schema enforcement requirements for readable-content success, diagnostic severity, and debug conditional presence.
- Clarified archive safety precedence, encrypted entry handling, compression-ratio formula, and security-before-OPF parsing.
- Defined public runtime return type, thread-safety expectation, invalid `input_path` behavior, and canonical builder invalid-input policy.
- Clarified CLI `--config -`, output overwrite, atomic write, malformed UTF-8 config, stdout pipe, and output-size measurement behavior.
- Added optional structured diagnostic affected-entity fields.
- Added SemVer and breaking-change policy.
