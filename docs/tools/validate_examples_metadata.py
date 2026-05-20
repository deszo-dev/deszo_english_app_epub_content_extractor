from __future__ import annotations
import ast, json, sys
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
VALID_COVERAGE_MODES = {
    "direct_import_and_call",
    "direct_import_constructor",
    "direct_import_exception_handling",
    "returned_shape_field_assertion",
    "returned_shape_coverage",
    "field_assertion_coverage",
}

def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def load_yaml(path: str):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))

def require_file(errors: list[str], path: str | None) -> Path:
    if not path:
        errors.append("missing path value")
        return ROOT / "__missing__"
    p = ROOT / path
    if not p.is_file():
        errors.append(f"missing file: {path}")
    return p

def parse_python(path: Path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

def has_assert(tree: ast.AST) -> bool:
    return any(isinstance(node, ast.Assert) for node in ast.walk(tree))

def imported_modules(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names

def imported_names_from_target(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "epub_content_extractor":
            for alias in node.names:
                names.add(alias.name)
    return names

def main() -> None:
    errors: list[str] = []
    schema = load_json("docs/schemas/examples-manifest.schema.json")
    manifest = load_json("docs/contracts/examples-manifest.json")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(manifest)
    except Exception as exc:
        errors.append(f"examples-manifest schema validation failed: {exc}")
    api_entries = load_yaml("docs/contracts/api-contract.yaml").get("public_api", [])
    api_ids = {entry.get("id") for entry in api_entries}
    api_names = {entry.get("id"): entry.get("name") for entry in api_entries}
    for ex in manifest.get("examples", []):
        p = require_file(errors, ex.get("path"))
        tree = None
        if p.is_file():
            try:
                tree = parse_python(p)
                if "has_asserts" in ex.get("static_checks", []) and not ex.get("no_assert_required") and not has_assert(tree):
                    errors.append(f"example has no assert: {ex.get('path')}")
                for name in imported_modules(tree):
                    if name.startswith("epub_content_extractor.") and "._" in name:
                        errors.append(f"private target import in example {ex.get('path')}: {name}")
            except SyntaxError as exc:
                errors.append(f"syntax error in {ex.get('path')}: {exc}")
        coverage_items = ex.get("covers_api") or [{"api_id": api_id, "coverage_mode": "field_assertion_coverage"} for api_id in ex.get("covers_api_ids", [])]
        direct_names = imported_names_from_target(tree) if tree is not None else set()
        for item in coverage_items:
            api_id = item.get("api_id")
            mode = item.get("coverage_mode")
            if api_id not in api_ids:
                errors.append(f"unknown api id referenced by {ex.get('id')}: {api_id}")
            if mode not in VALID_COVERAGE_MODES:
                errors.append(f"invalid coverage_mode in {ex.get('id')} for {api_id}: {mode}")
            if mode in {"direct_import_and_call", "direct_import_constructor", "direct_import_exception_handling"}:
                api_name = api_names.get(api_id)
                if tree is not None and api_name not in direct_names:
                    errors.append(f"{ex.get('id')} claims direct coverage of {api_id} but does not import {api_name} from public API")
    print(f"examples: {len(manifest.get('examples', []))}")
    print(f"errors: {len(errors)}")
    if errors:
        for e in errors:
            print(f"- {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
