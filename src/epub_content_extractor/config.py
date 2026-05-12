from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .schema_utils import config_schema


SCHEMA_VERSION = "epub_content_extractor.v2.2"
EXTRACTOR_VERSION = "2.2.0"


@dataclass(slots=True)
class EpubContentExtractorConfig:
    include_front_matter_in_canonical_text: bool = False
    include_back_matter_in_canonical_text: bool = False
    include_footnotes_in_canonical_text: bool = False
    include_chapter_titles_in_canonical_text: bool = True
    include_section_titles_in_canonical_text: bool = False
    max_epub_size_bytes: int = 104857600
    max_html_document_size_bytes: int = 10485760
    max_text_block_chars: int = 100000
    pipeline_timeout_seconds: int = 120
    html_parse_timeout_seconds: int = 20
    max_archive_uncompressed_bytes: int = 524288000
    max_archive_entry_count: int = 10000
    max_archive_compression_ratio: int = 100
    max_toc_depth: int = 8
    max_diagnostic_count: int = 1000
    max_output_json_bytes: int = 524288000
    include_debug: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


DEFAULT_CONFIG = EpubContentExtractorConfig()

CANONICAL_TEXT_OPTION_KEYS = frozenset(
    {
        "include_front_matter_in_canonical_text",
        "include_back_matter_in_canonical_text",
        "include_footnotes_in_canonical_text",
        "include_chapter_titles_in_canonical_text",
        "include_section_titles_in_canonical_text",
    }
)


def default_config_dict() -> dict[str, object]:
    return DEFAULT_CONFIG.as_dict()


def normalize_config_input(
    config: EpubContentExtractorConfig | dict[str, object] | None,
) -> dict[str, object]:
    if config is None:
        return {}
    if isinstance(config, EpubContentExtractorConfig):
        return config.as_dict()
    if isinstance(config, dict):
        return dict(config)
    raise TypeError("config must be None, dict, or EpubContentExtractorConfig")


def validate_config_payload(payload: dict[str, object]) -> list[str]:
    validator = Draft202012Validator(config_schema(), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    return [error.message for error in errors]


def resolve_config(
    config: EpubContentExtractorConfig | dict[str, object] | None,
) -> tuple[EpubContentExtractorConfig | None, list[str]]:
    payload = normalize_config_input(config)
    errors = validate_config_payload(payload)
    if errors:
        return None, errors

    payload.pop("$schema", None)
    merged: dict[str, Any] = default_config_dict()
    merged.update(payload)
    return EpubContentExtractorConfig(**merged), []


def resolve_builder_options(options: dict[str, object] | None) -> dict[str, bool]:
    resolved = {
        key: bool(value)
        for key, value in default_config_dict().items()
        if key in CANONICAL_TEXT_OPTION_KEYS
    }
    if options is None:
        return resolved
    for key, value in options.items():
        if key not in CANONICAL_TEXT_OPTION_KEYS:
            raise ValueError(f"unsupported canonical text option: {key}")
        if not isinstance(value, bool):
            raise ValueError(f"canonical text option must be boolean: {key}")
        resolved[key] = value
    return resolved
