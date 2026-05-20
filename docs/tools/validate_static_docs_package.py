from __future__ import annotations
import ast, hashlib, json, re, sys
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

SCHEMA_TARGETS = [
    ("docs/contracts/docs-manifest.json", "docs/schemas/docs-manifest.schema.json"),
    ("docs/contracts/examples-manifest.json", "docs/schemas/examples-manifest.schema.json"),
    ("docs/contracts/fixture-manifest.json", "docs/schemas/fixture-manifest.schema.json"),
    ("docs/contracts/mutation-probes.json", "docs/schemas/mutation-probes.schema.json"),
    ("docs/contracts/validation-manifest.json", "docs/schemas/validation-manifest.schema.json"),
    ("docs/contracts/diagnostics-registry.json", "docs/schemas/diagnostics-registry.schema.json"),
    ("docs/contracts/error-registry.json", "docs/schemas/epub_content_extractor_error_registry.v3.0.schema.json"),
    ("docs/contracts/test-coverage-manifest.json", "docs/schemas/test-coverage-manifest.schema.json"),
    ("docs/contracts/api-contract.yaml", "docs/schemas/api-contract.schema.json"),
]

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


def load_data(path: str):
    return load_yaml(path) if path.endswith((".yaml", ".yml")) else load_json(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def require_file(errors: list[str], path: str | None) -> Path:
    if not path:
        errors.append("missing file path value")
        return ROOT / "__missing__"
    p = ROOT / path
    if not p.exists() or not p.is_file():
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


def markdown_links(text: str):
    for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        yield match.group(1).split()[0].strip("<>")


def strip_code_fences(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def validate_jsonschema_targets(errors: list[str]) -> int:
    count = 0
    for data_path, schema_path in SCHEMA_TARGETS:
        data_file = require_file(errors, data_path)
        schema_file = require_file(errors, schema_path)
        if not data_file.is_file() or not schema_file.is_file():
            continue
        try:
            data = load_data(data_path)
            schema = load_json(schema_path)
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(data)
            count += 1
        except Exception as exc:
            errors.append(f"schema validation failed: {data_path} against {schema_path}: {exc}")
    return count


def validate_contract_shape(errors: list[str]):
    contract = load_yaml("docs/contracts/api-contract.yaml")
    entries = contract.get("public_api", [])
    ids: set[str] = set()
    for idx, entry in enumerate(entries):
        api_id = entry.get("id")
        for key in ["id", "name", "kind", "import_path", "stability", "description", "docs_path", "docs_anchor"]:
            if not entry.get(key):
                errors.append(f"api entry #{idx} missing {key}")
        if api_id in ids:
            errors.append(f"duplicate api id: {api_id}")
        ids.add(api_id)
        if entry.get("kind") in {"function", "class"} and not entry.get("signature"):
            errors.append(f"api entry {api_id} missing signature")
        if entry.get("kind") == "exception" and not entry.get("trigger_condition"):
            errors.append(f"exception {api_id} missing trigger_condition")
        if not entry.get("examples"):
            errors.append(f"api entry {api_id} missing examples")
        docs_path = entry.get("docs_path")
        docs_anchor = entry.get("docs_anchor")
        if docs_path and docs_anchor:
            expected = f"<!-- api: {api_id} -->"
            if docs_anchor != expected:
                errors.append(f"api entry {api_id} has wrong docs_anchor: {docs_anchor!r}")
            p = require_file(errors, docs_path)
            if p.is_file():
                occurrences = p.read_text(encoding="utf-8").count(docs_anchor)
                if occurrences != 1:
                    errors.append(f"api anchor for {api_id} must occur once in {docs_path}, found {occurrences}")
    return contract, ids


def validate_examples(errors: list[str], api_ids: set[str]):
    manifest = load_json("docs/contracts/examples-manifest.json")
    contract = load_yaml("docs/contracts/api-contract.yaml")
    api_names = {entry.get("id"): entry.get("name") for entry in contract.get("public_api", [])}
    covered: set[str] = set()
    for ex in manifest.get("examples", []):
        path = ex.get("path")
        p = require_file(errors, path)
        tree = None
        if p.is_file():
            try:
                tree = parse_python(p)
            except SyntaxError as exc:
                errors.append(f"python syntax error in {path}: {exc}")
                continue
            if "has_asserts" in ex.get("static_checks", []) and not ex.get("no_assert_required") and not has_assert(tree):
                errors.append(f"example has no assert: {path}")
            private_target_imports = [name for name in imported_modules(tree) if name.startswith("epub_content_extractor.") and "._" in name]
            if private_target_imports:
                errors.append(f"example imports private target modules: {path}: {private_target_imports}")
        coverage_items = ex.get("covers_api") or [{"api_id": api_id, "coverage_mode": "field_assertion_coverage"} for api_id in ex.get("covers_api_ids", [])]
        imported_direct_names = imported_names_from_target(tree) if tree is not None else set()
        for item in coverage_items:
            api_id = item.get("api_id")
            mode = item.get("coverage_mode")
            if api_id not in api_ids:
                errors.append(f"example {ex.get('id')} references unknown api id: {api_id}")
            else:
                covered.add(api_id)
            if mode not in VALID_COVERAGE_MODES:
                errors.append(f"example {ex.get('id')} has invalid coverage_mode for {api_id}: {mode}")
            if mode in {"direct_import_and_call", "direct_import_constructor", "direct_import_exception_handling"}:
                api_name = api_names.get(api_id)
                if tree is not None and api_name not in imported_direct_names:
                    errors.append(f"example {ex.get('id')} claims direct coverage for {api_id} but does not import {api_name}")
    missing_coverage = api_ids - covered
    if missing_coverage:
        errors.append(f"api ids without example manifest coverage: {sorted(missing_coverage)}")
    return manifest


def validate_fixture_hashes(errors: list[str]):
    manifest = load_json("docs/contracts/fixture-manifest.json")
    count = 0
    fixture_ids: set[str] = set()
    for fixture in manifest.get("fixtures", []):
        fid = fixture.get("id")
        if fid in fixture_ids:
            errors.append(f"duplicate fixture id: {fid}")
        fixture_ids.add(fid)
        for info in fixture.get("files", []):
            path = info.get("path")
            p = require_file(errors, path)
            if p.is_file():
                count += 1
                if p.stat().st_size != info.get("bytes"):
                    errors.append(f"byte count mismatch: {path}")
                if sha256_file(p) != info.get("sha256"):
                    errors.append(f"sha256 mismatch: {path}")
    return manifest, count, fixture_ids


def validate_test_coverage(errors: list[str], fixture_ids: set[str], api_ids: set[str]):
    manifest = load_json("docs/contracts/test-coverage-manifest.json")
    covered_fixtures: set[str] = set()
    for test in manifest.get("tests", []):
        fid = test.get("fixture_id")
        if fid not in fixture_ids:
            errors.append(f"test coverage references unknown fixture id: {test.get('test_id')}: {fid}")
        else:
            covered_fixtures.add(fid)
        for key in ["input_fixture", "config_fixture", "expected_output"]:
            value = test.get(key)
            if value is not None:
                require_file(errors, value)
        requirement = test.get("requirement", "")
        if requirement.startswith("docs/"):
            req_path = requirement.split("#", 1)[0]
            require_file(errors, req_path)
    missing = fixture_ids - covered_fixtures
    if missing:
        errors.append(f"fixtures without test coverage manifest entries: {sorted(missing)}")
    return manifest


def validate_markdown_paths(errors: list[str]):
    manifest = load_json("docs/contracts/docs-manifest.json")
    for path in manifest.get("markdown_files", []):
        p = require_file(errors, path)
        if not p.is_file():
            continue
        text = strip_code_fences(p.read_text(encoding="utf-8"))
        for link in markdown_links(text):
            if not link or link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = link.split("#", 1)[0]
            if not target:
                continue
            resolved = (p.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(f"markdown link escapes package: {path}: {link}")
                continue
            if not resolved.exists():
                errors.append(f"missing markdown link target: {path}: {link}")
    return manifest


def validate_diagnostics(errors: list[str]):
    registry = load_json("docs/contracts/diagnostics-registry.json")
    seen: set[str] = set()
    for diag in registry.get("diagnostics", []):
        for key in ["code", "severity", "when_emitted", "can_appear_in_success"]:
            if key not in diag:
                errors.append(f"diagnostic missing {key}: {diag}")
        code = diag.get("code")
        if code in seen:
            errors.append(f"duplicate diagnostic code: {code}")
        seen.add(code)
    return registry


def validate_mutation_probes(errors: list[str]):
    manifest = load_json("docs/contracts/mutation-probes.json")
    static_executable = 0
    for probe in manifest.get("probes", []):
        for key in ["id", "target", "mutation", "expected_failure", "phase", "validator_command", "executable"]:
            if key not in probe or probe.get(key) in (None, ""):
                errors.append(f"mutation probe missing {key}: {probe}")
        if probe.get("phase") == "static_docs" and probe.get("executable") is True:
            static_executable += 1
    if static_executable < 8:
        errors.append(f"expected at least 8 executable static mutation probes, found {static_executable}")
    return manifest


def main() -> None:
    errors: list[str] = []
    docs_manifest = load_json("docs/contracts/docs-manifest.json")
    for path in docs_manifest.get("markdown_files", []):
        require_file(errors, path)
    for path in docs_manifest.get("schemas", []):
        p = require_file(errors, path)
        if p.is_file():
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"schema JSON parse error {path}: {exc}")
    for path in docs_manifest.get("contracts", []):
        p = require_file(errors, path)
        if p.is_file() and p.suffix == ".json":
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"contract JSON parse error {path}: {exc}")
        if p.is_file() and p.suffix in {".yaml", ".yml"}:
            try:
                load_yaml(path)
            except Exception as exc:
                errors.append(f"contract YAML parse error {path}: {exc}")
    schema_validations = validate_jsonschema_targets(errors)
    contract, api_ids = validate_contract_shape(errors)
    examples_manifest = validate_examples(errors, api_ids)
    fixture_manifest, fixture_file_count, fixture_ids = validate_fixture_hashes(errors)
    test_coverage_manifest = validate_test_coverage(errors, fixture_ids, api_ids)
    validate_markdown_paths(errors)
    diag_registry = validate_diagnostics(errors)
    mutation_manifest = validate_mutation_probes(errors)
    expected_outputs = list((ROOT / "docs/testing/fixtures/expected").glob("*.json"))
    golden_files = [p for p in (ROOT / "docs/testing/goldens").glob("*") if p.is_file() and p.name.lower() != "readme.md"]
    print("static documentation package validation complete")
    print(f"normative_markdown_files: {len(docs_manifest.get('markdown_files', []))}")
    print(f"schemas: {len(docs_manifest.get('schemas', []))}")
    print(f"schema_validations: {schema_validations}")
    print(f"api_contract_entries: {len(contract.get('public_api', []))}")
    print(f"examples: {len(examples_manifest.get('examples', []))}")
    print(f"fixtures: {fixture_file_count}")
    print(f"fixture_sets: {len(fixture_manifest.get('fixtures', []))}")
    print(f"test_coverage_entries: {len(test_coverage_manifest.get('tests', []))}")
    print(f"expected_outputs: {len(expected_outputs)}")
    print(f"goldens: {len(golden_files)}")
    print(f"diagnostics: {len(diag_registry.get('diagnostics', []))}")
    print(f"mutation_probes: {len(mutation_manifest.get('probes', []))}")
    print("missing_paths: 0" if not [e for e in errors if "missing" in e] else "missing_paths: >0")
    print(f"errors: {len(errors)}")
    if errors:
        print("\nErrors:")
        for item in errors:
            print(f"- {item}")
        sys.exit(1)

if __name__ == "__main__":
    main()
