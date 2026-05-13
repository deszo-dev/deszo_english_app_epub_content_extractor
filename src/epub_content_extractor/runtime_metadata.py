from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Literal, cast

CompatibilityMode = Literal[
    "exact",
    "semver_compatible",
    "schema_compatible",
    "hash_exact",
]


@dataclass(frozen=True, slots=True)
class RuntimeDependency:
    name: str
    version: str
    source: str
    compatibility: CompatibilityMode = "exact"
    source_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class RuntimeAsset:
    name: str
    kind: str
    sha256: str
    compatibility: CompatibilityMode = "hash_exact"


@dataclass(frozen=True, slots=True)
class StageRuntimeMetadata:
    stage_name: str
    stage_contract_version: str
    output_schema_version: str
    config_contract_version: str
    module_version: str
    source_fingerprint: str | None = None
    dependencies: list[RuntimeDependency] = field(default_factory=list)
    assets: list[RuntimeAsset] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PipelineRuntimeMetadata:
    pipeline_name: str
    pipeline_version: str
    pipeline_contract_version: str
    stages: dict[str, StageRuntimeMetadata]


def runtime_metadata() -> PipelineRuntimeMetadata:
    root = project_root()
    package_root = root / "src" / "epub_content_extractor"
    schema_root = root / "docs" / "architecture" / "schema"
    pipeline_version = get_module_version("epub-content-extractor")

    stages = [
        StageRuntimeMetadata(
            stage_name="epub_document_reading",
            stage_contract_version="3.0",
            output_schema_version="epub-html-documents.v3.0",
            config_contract_version="epub-content-extractor-config.v3.0",
            module_version=pipeline_version,
            source_fingerprint=source_fingerprint_for_paths(
                root,
                [
                    package_root / "adapters" / "epub.py",
                    package_root / "config.py",
                    package_root / "exceptions.py",
                    package_root / "extractor.py",
                    schema_root / "epub_content_extractor_config.v3.0.schema.json",
                ],
            ),
            dependencies=[
                package_dependency("ebooklib"),
                package_dependency("beautifulsoup4"),
                package_dependency("lxml"),
            ],
        ),
        StageRuntimeMetadata(
            stage_name="html_block_extraction",
            stage_contract_version="3.0",
            output_schema_version="text-blocks.v3.0",
            config_contract_version="epub-content-extractor-config.v3.0",
            module_version=pipeline_version,
            source_fingerprint=source_fingerprint_for_paths(
                root,
                [
                    package_root / "adapters" / "html.py",
                    package_root / "config.py",
                    package_root / "core" / "constants.py",
                    package_root / "core" / "models.py",
                    package_root / "core" / "text.py",
                    package_root / "extractor.py",
                ],
            ),
            dependencies=[
                package_dependency("beautifulsoup4"),
                package_dependency("lxml"),
                package_dependency("ftfy"),
            ],
        ),
        StageRuntimeMetadata(
            stage_name="content_extraction",
            stage_contract_version="3.0",
            output_schema_version="epub_content_extractor.v3.0",
            config_contract_version="epub-content-extractor-config.v3.0",
            module_version=pipeline_version,
            source_fingerprint=source_fingerprint_for_paths(
                root,
                [
                    package_root / "config.py",
                    package_root / "exceptions.py",
                    package_root / "extractor.py",
                    package_root / "schema_utils.py",
                    schema_root / "epub_content_extractor.v3.0.schema.json",
                    schema_root / "epub_content_extractor_config.v3.0.schema.json",
                    schema_root / "epub_content_extractor_diagnostic_registry.v3.0.json",
                    schema_root / "epub_content_extractor_error_registry.v3.0.json",
                ],
            ),
            dependencies=[
                package_dependency("ftfy"),
                package_dependency("regex"),
                package_dependency("rapidfuzz"),
            ],
        ),
    ]

    return PipelineRuntimeMetadata(
        pipeline_name="epub_content_extractor",
        pipeline_version=pipeline_version,
        pipeline_contract_version="3.0",
        stages={stage.stage_name: stage for stage in stages},
    )


def stage_fingerprint(
    stage: StageRuntimeMetadata,
    *,
    pipeline_contract_version: str,
    normalized_stage_config_hash: str,
    input_artifact_hashes: dict[str, str],
) -> str:
    payload = {
        "stage_name": stage.stage_name,
        "stage_contract_version": stage.stage_contract_version,
        "output_schema_version": stage.output_schema_version,
        "config_contract_version": stage.config_contract_version,
        "normalized_stage_config_hash": normalized_stage_config_hash,
        "input_artifact_hashes": dict(sorted(input_artifact_hashes.items())),
        "module_version": stage.module_version,
        "source_fingerprint": stage.source_fingerprint,
        "dependencies": sorted(
            [asdict(dependency) for dependency in stage.dependencies],
            key=lambda value: value["name"],
        ),
        "assets": sorted(
            [asdict(asset) for asset in stage.assets],
            key=lambda value: (value["name"], value["kind"]),
        ),
        "pipeline_contract_version": pipeline_contract_version,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def canonical_json(value: object) -> str:
    serializable = (
        asdict(cast(Any, value))
        if not isinstance(value, type) and is_dataclass(value)
        else value
    )
    return json.dumps(
        serializable,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def source_fingerprint_for_paths(root: Path, paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"tree-sha256:{digest.hexdigest()}"


def directory_source_fingerprint(root: Path) -> str:
    relevant_suffixes = {
        ".py",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".sql",
        ".txt",
    }
    ignored_dirs = {
        "__pycache__",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".venv",
        "node_modules",
    }
    paths = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in relevant_suffixes
        and not any(part in ignored_dirs for part in path.parts)
    ]
    return source_fingerprint_for_paths(root, paths)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_dependency(name: str) -> RuntimeDependency:
    return RuntimeDependency(
        name=name,
        version=get_module_version(name),
        source="package",
        compatibility="exact",
    )


def get_module_version(distribution_name: str) -> str:
    try:
        return metadata.version(distribution_name)
    except metadata.PackageNotFoundError:
        return "unknown"


def project_root() -> Path:
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return path.parents[2]
