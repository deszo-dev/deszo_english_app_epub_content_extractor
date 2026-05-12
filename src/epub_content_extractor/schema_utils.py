from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def project_root() -> Path:
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return path.parents[2]


def schema_dir() -> Path:
    return project_root() / "docs" / "architecture" / "schema"


@lru_cache(maxsize=4)
def load_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def result_schema() -> dict[str, Any]:
    return load_json_file(schema_dir() / "epub_content_extractor.v2.2.schema.json")


@lru_cache(maxsize=1)
def config_schema() -> dict[str, Any]:
    return load_json_file(
        schema_dir() / "epub_content_extractor_config.v2.2.schema.json"
    )


@lru_cache(maxsize=1)
def diagnostic_registry() -> dict[str, Any]:
    return load_json_file(
        schema_dir() / "epub_content_extractor_diagnostic_registry.v2.2.json"
    )


@lru_cache(maxsize=1)
def error_registry() -> dict[str, Any]:
    return load_json_file(
        schema_dir() / "epub_content_extractor_error_registry.v2.2.json"
    )
