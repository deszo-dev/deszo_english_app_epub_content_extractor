# `epub_content_extractor` Contract-First Documentation

`epub_content_extractor` converts local `.epub` files into a structured, JSON-serializable book extraction result for downstream English NLP and language-learning pipelines.

This package is **contract-first**: it defines the module as a normative implementation target. Final code is not required for static documentation review.

## Contract scope

Owned by this module:

- Python library API for EPUB extraction;
- Python canonical text builder API;
- CLI behavior and exit-code expectations;
- output/result schema;
- closed config schema;
- diagnostics and structured error registries;
- static documentation validation;
- post-implementation conformance validation.

Not owned by this module: HTTP APIs, auth, DB persistence, queues, remote storage, OCR, visual rendering, CSS/page layout, and downstream NLP segmentation.

## Start here

1. Read [How to Start](how-to-start.md).
2. Read [Source of Truth](source-of-truth.md).
3. Read [Public API](public-api.md).
4. Run static validation from [Validation Guide](validation-guide.md).
5. Use [Post-Implementation Validation](post-implementation-validation.md) only after implementation exists.
