from __future__ import annotations
import json, sys
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FAMILIES = {
    "PROBE-MD-PATH-ALL",
    "PROBE-MANIFEST-HASH",
    "PROBE-API-CONTRACT-ID",
    "PROBE-EXAMPLE-NO-ASSERT",
    "PROBE-API-DOCS-ANCHOR",
    "PROBE-MANIFEST-SCHEMA",
    "PROBE-TEST-COVERAGE-FIXTURE",
    "PROBE-DIAGNOSTICS-REGISTRY-SCHEMA",
    "PROBE-EXAMPLE-COVERAGE-MODE",
    "PROBE-IMPLEMENTATION-SIGNATURE-DRIFT",
}

def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def main() -> None:
    errors: list[str] = []
    schema = load_json("docs/schemas/mutation-probes.schema.json")
    manifest = load_json("docs/contracts/mutation-probes.json")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(manifest)
    except Exception as exc:
        errors.append(f"mutation-probes schema validation failed: {exc}")
    ids = {probe.get("id") for probe in manifest.get("probes", [])}
    missing = REQUIRED_FAMILIES - ids
    if missing:
        errors.append(f"missing required mutation probe families: {sorted(missing)}")
    for probe in manifest.get("probes", []):
        for key in ["id", "priority", "phase", "target", "mutation", "expected_failure", "validator_command", "executable"]:
            if key not in probe or probe.get(key) in (None, ""):
                errors.append(f"probe missing {key}: {probe}")
        if probe.get("phase") == "static_docs" and probe.get("executable") is not True:
            errors.append(f"static docs probe must be executable: {probe.get('id')}")
        if probe.get("phase") == "post_implementation" and probe.get("implementation_required") is not True:
            errors.append(f"post-implementation probe must declare implementation_required=true: {probe.get('id')}")
    print(f"mutation probes: {len(manifest.get('probes', []))}")
    print(f"executable_static_probes: {sum(1 for p in manifest.get('probes', []) if p.get('phase') == 'static_docs' and p.get('executable'))}")
    print(f"errors: {len(errors)}")
    if errors:
        for e in errors:
            print(f"- {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
