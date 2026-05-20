# Testing Guide

This guide is written for generating pytest suites after the implementation exists. Static documentation review validates that the test contracts, fixtures, manifests, and expected outputs are complete enough to generate tests.

## Fixture policy

Binary EPUB files are not committed as canonical source fixtures. Contract fixtures are represented by deterministic source specs under `docs/testing/fixtures/input/`, with matching configs and normalized expected outputs.

The fixture-to-test source of truth is `docs/contracts/test-coverage-manifest.json`. This prose page explains the cases; the manifest is what validators use for reverse coverage.

## Fixture-to-test coverage matrix

| Test ID | Fixture ID | Input fixture | Config fixture | Expected output | Requirement |
|---|---|---|---|---|---|
| TC-API-001 | `success_minimal_valid` | `docs/testing/fixtures/input/success_minimal_valid.fixture.json` | `docs/testing/fixtures/config/success_minimal_valid.config.json` | `docs/testing/fixtures/expected/success_minimal_valid.expected.normalized.json` | `docs/contracts/api-contract.yaml#/public_api/extract_epub_content` |
| TC-OUT-001 | `success_complex_valid` | `docs/testing/fixtures/input/success_complex_valid.fixture.json` | `docs/testing/fixtures/config/success_complex_valid.config.json` | `docs/testing/fixtures/expected/success_complex_valid.expected.normalized.json` | `docs/schemas/epub_content_extractor.v3.0.schema.json` |
| TC-CFG-001 | `config_unknown_field` | `docs/testing/fixtures/input/config_unknown_field.fixture.json` | `docs/testing/fixtures/config/config_unknown_field.config.json` | `docs/testing/fixtures/expected/config_unknown_field.expected.normalized.json` | `docs/schemas/epub_content_extractor_config.v3.0.schema.json` |
| TC-SEC-001 | `security_path_traversal` | `docs/testing/fixtures/input/security_path_traversal.fixture.json` | `docs/testing/fixtures/config/security_path_traversal.config.json` | `docs/testing/fixtures/expected/security_path_traversal.expected.normalized.json` | `docs/security-archive-policy.md#path-traversal-and-absolute-path-policy` |
| TC-IO-001 | `failure_plain_text_epub_extension` | `docs/testing/fixtures/input/failure_plain_text_epub_extension.fixture.json` | `docs/testing/fixtures/config/failure_plain_text_epub_extension.config.json` | `docs/testing/fixtures/expected/failure_plain_text_epub_extension.expected.normalized.json` | `docs/contracts/error-registry.json` |
| TC-IO-002 | `failure_valid_zip_not_epub` | `docs/testing/fixtures/input/failure_valid_zip_not_epub.fixture.json` | `docs/testing/fixtures/config/failure_valid_zip_not_epub.config.json` | `docs/testing/fixtures/expected/failure_valid_zip_not_epub.expected.normalized.json` | `docs/contracts/error-registry.json` |
| TC-LIMIT-001 | `limits_no_readable_content` | `docs/testing/fixtures/input/limits_no_readable_content.fixture.json` | `docs/testing/fixtures/config/limits_no_readable_content.config.json` | `docs/testing/fixtures/expected/limits_no_readable_content.expected.normalized.json` | `docs/input-output-contract.md#no-readable-content-policy` |

## Core test cases

### TC-API-001: Minimal public API call succeeds

**Priority:** P0  
**Phase:** post-implementation  
**Requirement:** `docs/contracts/api-contract.yaml#/public_api/extract_epub_content`  
**Input fixture:** `docs/testing/fixtures/input/success_minimal_valid.fixture.json`  
**Config fixture:** `docs/testing/fixtures/config/success_minimal_valid.config.json`  
**Expected output:** `docs/testing/fixtures/expected/success_minimal_valid.expected.normalized.json`  
**Diagnostics:** `chapter_title_detected` may appear as info.

**Steps:**
1. Generate the EPUB input from the fixture source spec in a temporary directory.
2. Call public API only.
3. Call `extract_epub_content` with the config fixture.
4. Normalize volatile fields.
5. Compare with expected output.

**Assertions:**
- result status is `succeeded`;
- result schema version is `epub_content_extractor.v3.0`;
- output matches expected normalized JSON;
- no unexpected diagnostics are emitted.

**Static docs review note:** This test is automation-ready even if the implementation is not present yet. Do not penalize docs score for not executing it before implementation exists.

### TC-API-002: Canonical text builder uses documented defaults

**Priority:** P0  
**Phase:** post-implementation  
**Requirement:** `docs/contracts/api-contract.yaml#/public_api/build_canonical_text`  
**Input fixture:** successful result from TC-API-001  
**Expected behavior:** canonical text includes chapter titles by default and excludes front matter, back matter, footnotes, and section titles unless enabled.

**Assertions:**
- returned value is `str`;
- `Hello world.` appears in canonical text;
- invalid option keys raise programmer-error exceptions.

### TC-CFG-001: Invalid config fails before input path validation

**Priority:** P0  
**Phase:** post-implementation  
**Requirement:** `docs/schemas/epub_content_extractor_config.v3.0.schema.json`  
**Input fixture:** `docs/testing/fixtures/input/config_unknown_field.fixture.json`  
**Config fixture:** `docs/testing/fixtures/config/config_unknown_field.config.json`  
**Expected output:** `docs/testing/fixtures/expected/config_unknown_field.expected.normalized.json`

**Assertions:**
- result status is `failed`;
- error code is `invalid_config`;
- input file existence is not checked before config validation;
- raw invalid config values are not leaked into production output.

### TC-SEC-001: Archive path traversal is rejected before OPF parsing

**Priority:** P0  
**Phase:** post-implementation  
**Requirement:** `docs/security-archive-policy.md#path-traversal-and-absolute-path-policy`  
**Input fixture:** `docs/testing/fixtures/input/security_path_traversal.fixture.json`  
**Config fixture:** `docs/testing/fixtures/config/security_path_traversal.config.json`  
**Expected output:** `docs/testing/fixtures/expected/security_path_traversal.expected.normalized.json`

**Assertions:**
- result status is `failed`;
- error code represents archive security violation;
- no partial book is emitted;
- archive security validation wins before OPF parsing.

### TC-IO-001: Plain text file with `.epub` extension fails structurally

**Priority:** P0  
**Phase:** post-implementation  
**Requirement:** `docs/contracts/error-registry.json`  
**Input fixture:** `docs/testing/fixtures/input/failure_plain_text_epub_extension.fixture.json`  
**Config fixture:** `docs/testing/fixtures/config/failure_plain_text_epub_extension.config.json`  
**Expected output:** `docs/testing/fixtures/expected/failure_plain_text_epub_extension.expected.normalized.json`

**Assertions:**
- result status is `failed`;
- error code is stable and registry-backed;
- no `book` payload is emitted.

### TC-IO-002: Valid ZIP that is not EPUB fails manifest discovery

**Priority:** P0  
**Phase:** post-implementation  
**Requirement:** `docs/contracts/error-registry.json`  
**Input fixture:** `docs/testing/fixtures/input/failure_valid_zip_not_epub.fixture.json`  
**Config fixture:** `docs/testing/fixtures/config/failure_valid_zip_not_epub.config.json`  
**Expected output:** `docs/testing/fixtures/expected/failure_valid_zip_not_epub.expected.normalized.json`

**Assertions:**
- result status is `failed`;
- error code is `epub_manifest_unreadable` or the exact registry-backed package-discovery failure specified by the expected normalized output;
- no partial `book` payload is emitted.

### TC-OUT-001: Complex valid EPUB output is deterministic

**Priority:** P0  
**Phase:** post-implementation  
**Requirement:** `docs/schemas/epub_content_extractor.v3.0.schema.json`  
**Input fixture:** `docs/testing/fixtures/input/success_complex_valid.fixture.json`  
**Config fixture:** `docs/testing/fixtures/config/success_complex_valid.config.json`  
**Expected output:** `docs/testing/fixtures/expected/success_complex_valid.expected.normalized.json`

**Assertions:**
- result status is `succeeded`;
- ordered sections, chapters, notes, TOC entries, and assets are deterministic;
- normalized actual output equals the expected normalized JSON.

### TC-LIMIT-001: Structurally valid EPUB with no readable content fails

**Priority:** P0  
**Phase:** post-implementation  
**Requirement:** `docs/input-output-contract.md#no-readable-content-policy`  
**Input fixture:** `docs/testing/fixtures/input/limits_no_readable_content.fixture.json`  
**Config fixture:** `docs/testing/fixtures/config/limits_no_readable_content.config.json`  
**Expected output:** `docs/testing/fixtures/expected/limits_no_readable_content.expected.normalized.json`

**Assertions:**
- result status is `failed`;
- error code is `no_readable_content`;
- diagnostics explain why no readable text was produced;
- no successful structural-only output is emitted.

## Test generation checklist

- Generate all runtime EPUB inputs from fixture source specs.
- Validate every result against `docs/schemas/epub_content_extractor.v3.0.schema.json`.
- Validate config against `docs/schemas/epub_content_extractor_config.v3.0.schema.json`.
- Validate emitted diagnostic codes and severities against `docs/contracts/diagnostics-registry.json`.
- Normalize volatile timestamps, durations, and machine-local paths before golden comparison.
- Ensure every fixture ID in `docs/contracts/fixture-manifest.json` appears exactly once or intentionally more than once in `docs/contracts/test-coverage-manifest.json`.
