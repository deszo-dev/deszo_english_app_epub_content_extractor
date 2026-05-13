from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .schema_utils import canonical_text_build_options_schema, config_schema


SCHEMA_VERSION = "epub_content_extractor.v3.0"
EXTRACTOR_VERSION = "3.0.0"


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


@dataclass(frozen=True, slots=True)
class EpubCanonicalTextBuildOptions:
    include_front_matter: bool = False
    include_back_matter: bool = False
    include_footnotes: bool = False
    include_chapter_titles: bool = True
    include_section_titles: bool = False

    def as_dict(self) -> dict[str, bool]:
        return asdict(self)


CANONICAL_TEXT_OPTION_KEYS = frozenset(
    {
        "include_front_matter_in_canonical_text",
        "include_back_matter_in_canonical_text",
        "include_footnotes_in_canonical_text",
        "include_chapter_titles_in_canonical_text",
        "include_section_titles_in_canonical_text",
    }
)

# Mapping between config-level option names and the canonical-builder option names.
CONFIG_TO_BUILDER_OPTION = {
    "include_front_matter_in_canonical_text": "include_front_matter",
    "include_back_matter_in_canonical_text": "include_back_matter",
    "include_footnotes_in_canonical_text": "include_footnotes",
    "include_chapter_titles_in_canonical_text": "include_chapter_titles",
    "include_section_titles_in_canonical_text": "include_section_titles",
}

BUILDER_OPTION_KEYS = frozenset(CONFIG_TO_BUILDER_OPTION.values())


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


def default_builder_options_dict() -> dict[str, bool]:
    """Return canonical-builder option defaults derived from the default config."""
    config_defaults = default_config_dict()
    return {
        builder_key: bool(config_defaults[config_key])
        for config_key, builder_key in CONFIG_TO_BUILDER_OPTION.items()
    }


def resolve_builder_options(
    options: EpubCanonicalTextBuildOptions | dict[str, object] | None,
) -> dict[str, bool]:
    """Return a fully-resolved builder option dict keyed by v3.0 short names.

    Accepts:
    - ``None`` → defaults from config schema;
    - ``EpubCanonicalTextBuildOptions`` instance;
    - dict with either v3.0 short keys (``include_front_matter``, etc.) or
      legacy v2.2 config-level keys (``include_front_matter_in_canonical_text``).
    Raises ``ValueError``/``TypeError`` for unknown keys or non-bool values.
    """
    resolved = default_builder_options_dict()
    if options is None:
        return resolved
    if isinstance(options, EpubCanonicalTextBuildOptions):
        resolved.update(options.as_dict())
        return resolved
    if not isinstance(options, dict):
        raise TypeError(
            "options must be None, dict, or EpubCanonicalTextBuildOptions"
        )
    for key, value in options.items():
        if key in BUILDER_OPTION_KEYS:
            builder_key = key
        elif key in CANONICAL_TEXT_OPTION_KEYS:
            builder_key = CONFIG_TO_BUILDER_OPTION[key]
        else:
            raise ValueError(f"unsupported canonical text option: {key}")
        if not isinstance(value, bool):
            raise ValueError(f"canonical text option must be boolean: {key}")
        resolved[builder_key] = value
    return resolved
