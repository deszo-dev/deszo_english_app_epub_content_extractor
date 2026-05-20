# Models


## `EpubContentExtractorConfig`

<!-- api: EpubContentExtractorConfig -->

### Purpose

Typed representation of the closed extractor configuration schema.

### Import

```python
from epub_content_extractor import EpubContentExtractorConfig
```

### Signature

```python
EpubContentExtractorConfig(**fields)
```

### Fields

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `include_front_matter_in_canonical_text` | `boolean` | False | `False` |  |
| `include_back_matter_in_canonical_text` | `boolean` | False | `False` |  |
| `include_footnotes_in_canonical_text` | `boolean` | False | `False` |  |
| `include_chapter_titles_in_canonical_text` | `boolean` | False | `True` |  |
| `include_section_titles_in_canonical_text` | `boolean` | False | `False` |  |
| `max_epub_size_bytes` | `integer` | False | `104857600` |  |
| `max_html_document_size_bytes` | `integer` | False | `10485760` |  |
| `max_text_block_chars` | `integer` | False | `100000` |  |
| `pipeline_timeout_seconds` | `integer` | False | `120` |  |
| `html_parse_timeout_seconds` | `integer` | False | `20` |  |
| `max_archive_uncompressed_bytes` | `integer` | False | `524288000` |  |
| `max_archive_entry_count` | `integer` | False | `10000` |  |
| `max_archive_compression_ratio` | `integer` | False | `100` |  |
| `max_toc_depth` | `integer` | False | `8` |  |
| `max_diagnostic_count` | `integer` | False | `1000` |  |
| `max_output_json_bytes` | `integer` | False | `524288000` |  |
| `include_debug` | `boolean` | False | `False` |  |

### Raises

Model construction may raise `TypeError` or `ValueError` for programmer-error input.

### Side effects

None.

### Minimal example

```python
# See related examples for construction and assertions.
```

### Contract assertions

```python
assert EpubContentExtractorConfig is not None
```

### Related examples

- `examples/public_api_examples.py`


## `EpubCanonicalTextBuildOptions`

<!-- api: EpubCanonicalTextBuildOptions -->

### Purpose

Typed representation of canonical text builder options.

### Import

```python
from epub_content_extractor import EpubCanonicalTextBuildOptions
```

### Signature

```python
EpubCanonicalTextBuildOptions(**fields)
```

### Fields

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `include_front_matter` | `boolean` | False | `False` |  |
| `include_back_matter` | `boolean` | False | `False` |  |
| `include_footnotes` | `boolean` | False | `False` |  |
| `include_chapter_titles` | `boolean` | False | `True` |  |
| `include_section_titles` | `boolean` | False | `False` |  |

### Raises

Model construction may raise `TypeError` or `ValueError` for programmer-error input.

### Side effects

None.

### Minimal example

```python
# See related examples for construction and assertions.
```

### Contract assertions

```python
assert EpubCanonicalTextBuildOptions is not None
```

### Related examples

- `examples/public_api_examples.py`


## `EpubContentExtractionResult`

<!-- api: EpubContentExtractionResult -->

### Purpose

Top-level extraction result model matching the official result JSON Schema.

### Import

```python
from epub_content_extractor import EpubContentExtractionResult
```

### Signature

```python
EpubContentExtractionResult(...)
```

### Fields

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `schema_version` | `schema-defined` | True | `None` |  |
| `status` | `schema-defined` | True | `None` |  |
| `book` | `schema-defined` | False | `None` |  |
| `error` | `schema-defined` | False | `None` |  |
| `diagnostics` | `schema-defined` | True | `None` |  |
| `extraction` | `schema-defined` | True | `None` |  |
| `debug` | `schema-defined` | False | `None` |  |

### Raises

Model construction may raise `TypeError` or `ValueError` for programmer-error input.

### Side effects

None.

### Minimal example

```python
# See related examples for construction and assertions.
```

### Contract assertions

```python
assert EpubContentExtractionResult is not None
```

### Related examples

- `examples/how_to_start.py`
- `examples/error_handling.py`


## `EpubBook`

<!-- api: EpubBook -->

### Purpose

Structured extracted book model available on succeeded results.

### Import

```python
from epub_content_extractor import EpubBook
```

### Signature

```python
EpubBook(...)
```

### Fields

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `title` | `schema-defined` | True | `None` |  |
| `subtitle` | `schema-defined` | True | `None` |  |
| `language` | `schema-defined` | True | `None` |  |
| `authors` | `schema-defined` | True | `None` |  |
| `contributors` | `schema-defined` | True | `None` |  |
| `metadata` | `schema-defined` | True | `None` |  |
| `front_matter` | `schema-defined` | True | `None` |  |
| `chapters` | `schema-defined` | True | `None` |  |
| `back_matter` | `schema-defined` | True | `None` |  |
| `footnotes` | `schema-defined` | True | `None` |  |
| `table_of_contents` | `schema-defined` | True | `None` |  |
| `assets` | `schema-defined` | True | `None` |  |

### Raises

Model construction may raise `TypeError` or `ValueError` for programmer-error input.

### Side effects

None.

### Minimal example

```python
# See related examples for construction and assertions.
```

### Contract assertions

```python
assert EpubBook is not None
```

### Related examples

- `examples/public_api_examples.py`


## `EpubDiagnostic`

<!-- api: EpubDiagnostic -->

### Purpose

Production diagnostic emitted for non-fatal losses, uncertainty, or quality notes.

### Import

```python
from epub_content_extractor import EpubDiagnostic
```

### Signature

```python
EpubDiagnostic(code: str, severity: str, message: str, ...)
```

### Fields

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `code` | `schema-defined` | True | `None` |  |
| `severity` | `schema-defined` | True | `None` |  |
| `message` | `schema-defined` | True | `None` |  |
| `entity_type` | `schema-defined` | False | `None` |  |
| `entity_id` | `schema-defined` | False | `None` |  |
| `field` | `schema-defined` | False | `None` |  |

### Raises

Model construction may raise `TypeError` or `ValueError` for programmer-error input.

### Side effects

None.

### Minimal example

```python
# See related examples for construction and assertions.
```

### Contract assertions

```python
assert EpubDiagnostic is not None
```

### Related examples

- `examples/how_to_start.py`
- `examples/error_handling.py`


## `EpubExtractionError`

<!-- api: EpubExtractionError -->

### Purpose

Structured failed-result error object.

### Import

```python
from epub_content_extractor import EpubExtractionError
```

### Signature

```python
EpubExtractionError(code: str, message: str, recoverable: bool)
```

### Fields

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `code` | `schema-defined` | True | `None` |  |
| `message` | `schema-defined` | True | `None` |  |
| `recoverable` | `schema-defined` | True | `None` |  |

### Raises

Model construction may raise `TypeError` or `ValueError` for programmer-error input.

### Side effects

None.

### Minimal example

```python
# See related examples for construction and assertions.
```

### Contract assertions

```python
assert EpubExtractionError is not None
```

### Related examples

- `examples/error_handling.py`
