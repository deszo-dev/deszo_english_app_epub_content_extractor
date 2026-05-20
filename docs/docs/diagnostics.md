# Diagnostics and Errors

The canonical diagnostic registry is `docs/contracts/diagnostics-registry.json`.
The canonical structured error registry is `docs/contracts/error-registry.json`.

Human-readable `message` text is not stable API. Codes, severities, count behavior, and deterministic order are stable contract surfaces.

## Diagnostic rules

- Diagnostics are production output.
- Diagnostics must not contain full book text.
- Diagnostics must not contain absolute local file paths by default.
- Each diagnostic code has exactly one valid severity.

## Diagnostic registry summary

| Code | Severity | When emitted | Count impact | Can appear in success |
|---|---|---|---|---|
| `metadata_missing_title` | `warning` | No usable title metadata is available | warning +1 | `true` |
| `metadata_missing_author` | `info` | No usable author metadata is available | none | `true` |
| `metadata_language_missing` | `info` | EPUB language metadata is absent | none | `true` |
| `metadata_language_conflicts_with_contract` | `warning` | Metadata language is present and primarily non-English-like | warning +1 | `true` |
| `metadata_author_split_uncertain` | `warning` | Ambiguous creator string cannot be split safely | warning +1 | `true` |
| `metadata_date_invalid` | `warning` | Date metadata cannot be normalized losslessly | warning +1 | `true` |
| `table_of_contents_missing` | `info` | EPUB has no usable TOC | none | `true` |
| `toc_target_unresolved` | `warning` | TOC item target cannot be mapped to an internal output id | warning +1 | `true` |
| `chapter_title_detected` | `info` | A chapter title is confidently detected from heading/TOC | none | `true` |
| `chapter_title_uncertain` | `warning` | Chapter title candidate is ambiguous and omitted (reserved in v3.0; production code must not emit by default). | warning +1 | `true` |
| `chapter_type_uncertain` | `warning` | Chapter semantic type cannot be inferred (reserved in v3.0; production code must not emit by default). | warning +1 | `true` |
| `front_matter_detected` | `info` | A front matter section is detected | none | `true` |
| `back_matter_detected` | `info` | A back matter section is detected | none | `true` |
| `copyright_section_detected` | `info` | Copyright section is detected and structurally preserved/excluded from canonical text | none | `true` |
| `advertisement_section_detected` | `warning` | Advertisement section is detected | warning +1 | `true` |
| `publisher_notes_detected` | `info` | Publisher notes are detected | none | `true` |
| `table_of_contents_removed_from_canonical_text` | `info` | TOC-like text is removed from canonical text | none | `true` |
| `footnote_detected` | `info` | Footnote/endnote is detected | none | `true` |
| `footnote_marker_removed` | `info` | Inline marker is resolved and removed from paragraph text | none | `true` |
| `footnote_marker_unresolved` | `warning` | Inline marker cannot be resolved confidently | warning +1 | `true` |
| `footnote_owner_uncertain` | `warning` | Footnote cannot be assigned to chapter/section confidently | warning +1 | `true` |
| `footnote_duplicate_marker` | `warning` | Duplicate markers are ambiguous in one owner | warning +1 | `true` |
| `page_number_removed` | `info` | Page number artifact is removed | none | `true` |
| `repeated_header_footer_removed` | `info` | Repeated running header/footer is removed | none | `true` |
| `navigation_boilerplate_removed` | `info` | Navigation boilerplate is removed | none | `true` |
| `artifact_removed` | `info` | Decorative or layout artifact is removed | none | `true` |
| `unicode_normalized` | `info` | Text was normalized or mojibake was repaired | none | `true` |
| `unicode_normalization_failed` | `warning` | Text normalization/repair partially failed | warning +1 | `true` |
| `html_document_too_large_skipped` | `warning` | One HTML document exceeds `max_html_document_size_bytes` | warning +1 | `true` |
| `html_document_parse_timeout_skipped` | `warning` | One HTML document exceeds `html_parse_timeout_seconds` | warning +1 | `true` |
| `text_block_too_large_split` | `warning` | One block is split to respect `max_text_block_chars` | warning +1 | `true` |
| `text_block_too_large_dropped` | `warning` | One block cannot be split safely and is dropped (reserved in v3.0; production code must not emit by default). | warning +1 | `true` |
| `empty_readable_content` | `error` | Extraction reaches content analysis but no readable content remains | error +1 | `false` |
| `quality_warning` | `warning` | Generic deterministic quality warning or diagnostic truncation | warning +1 | `true` |

## Structured errors

| Code | When emitted | CLI exit code | Recoverable |
|---|---|---|---|
| `invalid_config` | Config file cannot be parsed as JSON or config fails schema validation | `4` | `false` |
| `input_file_not_found` | `input_path` does not exist, including broken symlink | `1` | `false` |
| `input_not_file` | `input_path` exists but is not a regular local file | `1` | `false` |
| `input_not_epub` | File cannot be opened as a ZIP-based EPUB container | `1` | `false` |
| `epub_file_too_large` | Input file bytes exceed `max_epub_size_bytes` | `1` | `false` |
| `epub_open_failed` | File appears to be accessible but EPUB container cannot be read after path/size checks, including permission/read errors | `1` | `false` |
| `epub_manifest_unreadable` | ZIP container opens but EPUB package/OPF manifest cannot be located or parsed | `1` | `false` |
| `epub_archive_security_violation` | Archive safety policy fails: path traversal, absolute internal path, excessive entries, excessive uncompressed bytes, excessive compression ratio, malformed central directory, or forbidden external resolution attempt | `1` | `false` |
| `no_readable_content` | Extraction completes or all readable candidates are skipped/dropped/timed out and no readable content remains | `1` | `false` |
| `pipeline_timeout` | Whole extraction exceeds `pipeline_timeout_seconds` | `1` | `false` |
| `output_write_failed` | Selected CLI output destination cannot be written | `3` | `false` |
| `internal_error` | Unexpected implementation defect | `99` | `false` |
