# Functions


## `extract_epub_content`

<!-- api: extract_epub_content -->

### Purpose

Extract a local EPUB file into a structured JSON-serializable result object.

### Import

```python
from epub_content_extractor import extract_epub_content
```

### Signature

```python
extract_epub_content(input_path: str | Path, config: EpubContentExtractorConfig | Mapping[str, object] | None = None) -> EpubContentExtractionResult
```

### Parameters

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `input_path` | `str | pathlib.Path` | True | `None` | Path to a local readable EPUB-like file. |
| `config` | `EpubContentExtractorConfig | Mapping[str, object] | None` | False | `None` | Optional closed extractor config. |

### Returns

Structured result with diagnostics, extraction metadata, and book or error.

### Raises

| Exception | When emitted | Recovery |
|---|---|---|
| `TypeError` | Programmer-error input such as input_path=None. | Pass str or pathlib.Path. |

### Side effects

Reads the local input file.

### Determinism

`true`

### Minimal example

```python
# See examples/how_to_start.py
```

### Contract assertions

```python
assert result is not None
```

### Related examples

- `examples/how_to_start.py`
- `examples/public_api_examples.py`
- `examples/batch_usage.py`
- `examples/error_handling.py`


## `build_canonical_text`

<!-- api: build_canonical_text -->

### Purpose

Build canonical plain text from an extracted book object.

### Import

```python
from epub_content_extractor import build_canonical_text
```

### Signature

```python
build_canonical_text(book: EpubBook | Mapping[str, object], options: EpubCanonicalTextBuildOptions | Mapping[str, bool] | None = None) -> str
```

### Parameters

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `book` | `EpubBook | Mapping[str, object]` | True | `None` | Book from a succeeded extraction. |
| `options` | `EpubCanonicalTextBuildOptions | Mapping[str, bool] | None` | False | `None` | Closed boolean option mapping. |

### Returns

Deterministically ordered canonical text.

### Raises

| Exception | When emitted | Recovery |
|---|---|---|
| `TypeError` | Book object has invalid shape. | Pass result.book from a succeeded extraction. |
| `ValueError` | Options contain unknown keys or non-boolean values. | Validate against options schema. |

### Side effects

None.

### Determinism

`true`

### Minimal example

```python
# See examples/public_api_examples.py
```

### Contract assertions

```python
assert result is not None
```

### Related examples

- `examples/public_api_examples.py`
- `examples/batch_usage.py`
