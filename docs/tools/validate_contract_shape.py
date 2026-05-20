from __future__ import annotations
import json, re, sys
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

def load_yaml(path: str):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))

def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def validate_against_schema(errors: list[str]) -> None:
    schema = load_json("docs/schemas/api-contract.schema.json")
    contract = load_yaml("docs/contracts/api-contract.yaml")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(contract)
    except Exception as exc:
        errors.append(f"api-contract schema validation failed: {exc}")

def validate_docs_anchor(errors: list[str], entry: dict) -> None:
    docs_path = entry.get("docs_path")
    docs_anchor = entry.get("docs_anchor")
    api_id = entry.get("id")
    if not docs_path:
        errors.append(f"api entry {api_id} missing docs_path")
        return
    if not docs_anchor:
        errors.append(f"api entry {api_id} missing docs_anchor")
        return
    expected = f"<!-- api: {api_id} -->"
    if docs_anchor != expected:
        errors.append(f"api entry {api_id} docs_anchor must be {expected!r}, got {docs_anchor!r}")
    path = ROOT / docs_path
    if not path.is_file():
        errors.append(f"api entry {api_id} docs_path does not exist: {docs_path}")
        return
    count = path.read_text(encoding="utf-8").count(docs_anchor)
    if count != 1:
        errors.append(f"api entry {api_id} docs_anchor must appear exactly once in {docs_path}, found {count}")

def main() -> None:
    errors: list[str] = []
    validate_against_schema(errors)
    contract = load_yaml("docs/contracts/api-contract.yaml")
    if contract.get("implementation_required_for_static_review") is not False:
        errors.append("implementation_required_for_static_review must be false")
    ids: set[str] = set()
    for entry in contract.get("public_api", []):
        api_id = entry.get("id")
        for key in ["id", "name", "kind", "import_path", "stability", "description", "docs_path", "docs_anchor"]:
            if not entry.get(key):
                errors.append(f"api entry missing {key}: {api_id}")
        if api_id in ids:
            errors.append(f"duplicate api id: {api_id}")
        ids.add(api_id)
        if entry.get("kind") in {"function", "class"} and not entry.get("signature"):
            errors.append(f"api entry missing signature: {api_id}")
        if entry.get("kind") == "exception" and not entry.get("trigger_condition"):
            errors.append(f"exception missing trigger condition: {api_id}")
        if not entry.get("examples"):
            errors.append(f"api entry missing examples: {api_id}")
        validate_docs_anchor(errors, entry)
    print(f"api contract entries: {len(ids)}")
    print(f"errors: {len(errors)}")
    if errors:
        for e in errors:
            print(f"- {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
