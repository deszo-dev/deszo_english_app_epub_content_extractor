# Public API

The normative API surface is `docs/contracts/api-contract.yaml`. Import paths are target paths for the current or future implementation.

| API ID | Name | Kind | Stability | Examples |
|---|---|---|---|---|
| `extract_epub_content` | `extract_epub_content` | `function` | `stable` | `examples/how_to_start.py`<br>`examples/public_api_examples.py`<br>`examples/batch_usage.py`<br>`examples/error_handling.py` |
| `build_canonical_text` | `build_canonical_text` | `function` | `stable` | `examples/public_api_examples.py`<br>`examples/batch_usage.py` |
| `EpubContentExtractorConfig` | `EpubContentExtractorConfig` | `dataclass_or_model` | `stable` | `examples/public_api_examples.py` |
| `EpubCanonicalTextBuildOptions` | `EpubCanonicalTextBuildOptions` | `dataclass_or_model` | `stable` | `examples/public_api_examples.py` |
| `EpubContentExtractionResult` | `EpubContentExtractionResult` | `dataclass_or_model` | `stable` | `examples/how_to_start.py`<br>`examples/error_handling.py` |
| `EpubBook` | `EpubBook` | `dataclass_or_model` | `stable` | `examples/public_api_examples.py` |
| `EpubDiagnostic` | `EpubDiagnostic` | `dataclass_or_model` | `stable` | `examples/how_to_start.py`<br>`examples/error_handling.py` |
| `EpubExtractionError` | `EpubExtractionError` | `dataclass_or_model` | `stable` | `examples/error_handling.py` |
| `EpubContentExtractorError` | `EpubContentExtractorError` | `exception` | `stable` | `examples/error_handling.py` |

## Core contract

- Domain failures return structured failed results where possible.
- Invalid config returns `status = "failed"` with `error.code = "invalid_config"`.
- Missing/unreadable/invalid EPUB files return structured failed results with error codes from `docs/contracts/error-registry.json`.
- Programmer errors may raise `TypeError`, `ValueError`, or `EpubContentExtractorError` if a structured result cannot be built.
- `book.language` is always `"en"` in the v3.0 contract.
