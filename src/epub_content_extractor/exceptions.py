from __future__ import annotations


class ExtractionError(Exception):
    """Base class for expected extraction errors."""


class InputValidationError(ExtractionError):
    """Raised when user-provided input violates the extractor preconditions."""


class EpubReadError(ExtractionError):
    """Raised when an EPUB cannot be read as structured document data."""


class PipelineInvariantError(ExtractionError):
    """Raised when core processing violates a documented invariant."""
