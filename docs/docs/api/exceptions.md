# Exceptions


## `EpubContentExtractorError`

<!-- api: EpubContentExtractorError -->

### Purpose

Base exception for unexpected implementation defects that prevent a structured result.

### Import

```python
from epub_content_extractor import EpubContentExtractorError
```

### Signature

```python
EpubContentExtractorError(message: str)
```

### Trigger condition

Unexpected implementation defect or environment failure that prevents construction of a structured failed result.

### Recovery

Treat as bug/operational failure; normal EPUB/config failures must be structured results.

### Minimal example

```python
try:
    ...
except EpubContentExtractorError:
    ...
```

### Contract assertions

```python
assert issubclass(EpubContentExtractorError, Exception)
```

### Related examples

- `examples/error_handling.py`
