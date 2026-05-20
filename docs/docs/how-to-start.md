# How to Start

## 1. Install the documentation package

```bash
python -m venv .venv
. .venv/bin/activate  # Linux/macOS
# .venv\\Scripts\\Activate.ps1  # Windows PowerShell
pip install -r requirements-docs.txt
```

## 2. Install the future implementation package

```bash
pip install epub_content_extractor
```

If the implementation package is not available yet, treat this page as a normative contract example for the future implementation.

## 3. Minimal API usage

```python
from pathlib import Path
from epub_content_extractor import extract_epub_content

result = extract_epub_content(Path("book.epub"), config={})

assert result is not None
assert result.status in {"succeeded", "failed"}
```

## 4. Expected successful result shape

```json
{
  "schema_version": "epub_content_extractor.v3.0",
  "status": "succeeded",
  "book": {"language": "en", "chapters": []},
  "diagnostics": [],
  "extraction": {"extractor_version": "3.0.0", "config": {}, "summary": {}}
}
```

## 5. Contract assertions

```python
assert result.schema_version == "epub_content_extractor.v3.0"
assert result.status == "succeeded"
assert result.book.language == "en"
assert isinstance(result.diagnostics, list)
```

## 6. View this documentation as HTML

See [HTML Viewing Guide](html-viewing-guide.md).

## 7. Full public API examples

See [Examples](examples.md) and the copy-paste-ready files in `examples/`.
