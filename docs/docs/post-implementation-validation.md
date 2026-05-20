# Post-Implementation Validation

This gate is intentionally separate from static documentation validation.

The documentation package can be rated 9+ as a static contract package before implementation exists, if all static documentation, manifests, schemas, examples metadata, fixtures and HTML build gates pass.

Run this only after implementation exists:

```bash
make validate-against-implementation
pytest examples/ -q
```

## Current executable checks

`tools/validate_against_implementation.py` performs these post-implementation checks:

1. every `import_path` in `docs/contracts/api-contract.yaml` resolves;
2. every public function/class/exception exists;
3. function and constructor signatures are compatible with the documented signature names;
4. dataclass/model fields are checked through dataclass fields, Pydantic-style `model_fields`, class annotations, or constructor parameters when available;
5. documented exception classes subclass `Exception`;
6. examples are syntax checked and, when `--run-examples` is provided, executed through `pytest`;
7. output schemas and registries are loaded so schema-path drift fails early.

## Non-goals during static docs review

Do not run this gate before implementation exists. Implementation absence must be reported as:

```text
Runtime proof: Not verified because implementation was not provided.
```

This is not a blocker for static documentation readiness.

## Required drift failures after implementation exists

The gate MUST fail when:

- a public API import path disappears;
- a public method/function removes or renames a documented parameter;
- a documented model field disappears from the implemented public model surface;
- the public exception no longer subclasses `Exception`;
- examples cannot be executed after installing the implementation package;
- runtime outputs do not validate against `docs/schemas/epub_content_extractor.v3.0.schema.json` in the future pytest suite.
