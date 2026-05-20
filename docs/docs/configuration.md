# Configuration

The canonical config schema is `docs/schemas/epub_content_extractor_config.v3.0.schema.json`.

The schema is closed. Unknown config fields are invalid, except the tooling-only input field `$schema`, which is accepted as an absolute URI and omitted from `extraction.config`.

## Extractor config fields

| Field | Type | Required | Default | Minimum | Maximum | Description |
|---|---|---|---|---|---|---|
| `$schema` | `string` | No | `` | `` | `` | Optional tooling-only absolute schema URI accepted in input config. Ignored during semantic config processing and omitted from extraction.config. |
| `include_front_matter_in_canonical_text` | `boolean` | No | `False` | `` | `` |  |
| `include_back_matter_in_canonical_text` | `boolean` | No | `False` | `` | `` |  |
| `include_footnotes_in_canonical_text` | `boolean` | No | `False` | `` | `` |  |
| `include_chapter_titles_in_canonical_text` | `boolean` | No | `True` | `` | `` |  |
| `include_section_titles_in_canonical_text` | `boolean` | No | `False` | `` | `` |  |
| `max_epub_size_bytes` | `integer` | No | `104857600` | `1` | `1073741824` |  |
| `max_html_document_size_bytes` | `integer` | No | `10485760` | `1` | `104857600` |  |
| `max_text_block_chars` | `integer` | No | `100000` | `1` | `1000000` |  |
| `pipeline_timeout_seconds` | `integer` | No | `120` | `1` | `3600` |  |
| `html_parse_timeout_seconds` | `integer` | No | `20` | `1` | `300` |  |
| `max_archive_uncompressed_bytes` | `integer` | No | `524288000` | `1` | `2147483648` |  |
| `max_archive_entry_count` | `integer` | No | `10000` | `1` | `100000` |  |
| `max_archive_compression_ratio` | `integer` | No | `100` | `1` | `1000` |  |
| `max_toc_depth` | `integer` | No | `8` | `1` | `64` |  |
| `max_diagnostic_count` | `integer` | No | `1000` | `1` | `100000` |  |
| `max_output_json_bytes` | `integer` | No | `524288000` | `1` | `1073741824` |  |
| `include_debug` | `boolean` | No | `False` | `` | `` |  |

## Canonical text build options

The canonical options schema is `docs/schemas/epub_canonical_text_build_options.v3.0.schema.json`.

| Field | Type | Default |
|---|---|---|
| `include_front_matter` | `boolean` | `False` |
| `include_back_matter` | `boolean` | `False` |
| `include_footnotes` | `boolean` | `False` |
| `include_chapter_titles` | `boolean` | `True` |
| `include_section_titles` | `boolean` | `False` |

## Config ordering rules

- Config validation happens before input path validation and EPUB parsing.
- Missing config is equivalent to `{}`.
- Numeric limit fields must be JSON integer numbers, not strings such as `"100MB"`.
- Values above hard schema maximums are invalid config.
