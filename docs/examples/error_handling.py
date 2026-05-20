"""Structured error-handling contract example."""
from pathlib import Path
from tempfile import TemporaryDirectory
from epub_content_extractor import EpubContentExtractorError, extract_epub_content

def value(obj, key):
    return obj[key] if isinstance(obj, dict) else getattr(obj, key)

with TemporaryDirectory() as tmp:
    missing_input = Path(tmp) / "missing.epub"
    invalid_config_result = extract_epub_content(missing_input, config={"unknown_field": True})
    assert value(invalid_config_result, "status") == "failed"
    assert value(value(invalid_config_result, "error"), "code") == "invalid_config"
    missing_file_result = extract_epub_content(missing_input, config={})
    assert value(missing_file_result, "status") == "failed"
    assert value(value(missing_file_result, "error"), "code") == "input_file_not_found"

try:
    extract_epub_content(None)  # type: ignore[arg-type]
except TypeError:
    pass
except EpubContentExtractorError:
    pass
else:
    raise AssertionError("input_path=None must not be treated as a normal domain failure")
