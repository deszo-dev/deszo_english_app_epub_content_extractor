from __future__ import annotations
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, data) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")


def mutate(copy_root: Path, probe_id: str) -> None:
    if probe_id == "PROBE-MD-PATH-ALL":
        p = copy_root / "docs/index.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n\n[Broken mutation link](missing-mutated-target.md)\n", encoding="utf-8")
    elif probe_id == "PROBE-MANIFEST-HASH":
        p = copy_root / "docs/testing/fixtures/config/success_minimal_valid.config.json"
        p.write_text(p.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    elif probe_id == "PROBE-API-CONTRACT-ID":
        p = copy_root / "docs/contracts/examples-manifest.json"
        data = load_json(p)
        data["examples"][0]["covers_api_ids"][0] = "UNKNOWN_MUTATED_API"
        data["examples"][0]["covers_api"][0]["api_id"] = "UNKNOWN_MUTATED_API"
        write_json(p, data)
    elif probe_id == "PROBE-EXAMPLE-NO-ASSERT":
        p = copy_root / "examples/how_to_start.py"
        lines = [line for line in p.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("assert ")]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif probe_id == "PROBE-API-DOCS-ANCHOR":
        p = copy_root / "docs/contracts/api-contract.yaml"
        data = load_yaml(p)
        data["public_api"][0].pop("docs_anchor", None)
        write_yaml(p, data)
    elif probe_id == "PROBE-MANIFEST-SCHEMA":
        p = copy_root / "docs/contracts/docs-manifest.json"
        data = load_json(p)
        data.pop("package", None)
        write_json(p, data)
    elif probe_id == "PROBE-TEST-COVERAGE-FIXTURE":
        p = copy_root / "docs/contracts/test-coverage-manifest.json"
        data = load_json(p)
        data["tests"] = data["tests"][:-1]
        write_json(p, data)
    elif probe_id == "PROBE-DIAGNOSTICS-REGISTRY-SCHEMA":
        p = copy_root / "docs/contracts/diagnostics-registry.json"
        data = load_json(p)
        data["diagnostics"][0].pop("severity", None)
        write_json(p, data)
    elif probe_id == "PROBE-EXAMPLE-COVERAGE-MODE":
        p = copy_root / "docs/contracts/examples-manifest.json"
        data = load_json(p)
        data["examples"][0]["covers_api"][0]["coverage_mode"] = "invalid_mutated_mode"
        write_json(p, data)
    else:
        raise ValueError(f"No executable mutator registered for {probe_id}")


def run_command(copy_root: Path, command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=copy_root, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)


def main() -> None:
    manifest = load_json(ROOT / "docs/contracts/mutation-probes.json")
    executable = [p for p in manifest.get("probes", []) if p.get("phase") == "static_docs" and p.get("executable") is True]
    failures: list[str] = []
    for probe in executable:
        probe_id = probe["id"]
        with tempfile.TemporaryDirectory(prefix=f"{probe_id.lower()}-") as tmp:
            copy_root = Path(tmp) / ROOT.name
            shutil.copytree(ROOT, copy_root, ignore=shutil.ignore_patterns("site", "__pycache__", "*.pyc"))
            try:
                mutate(copy_root, probe_id)
            except Exception as exc:
                failures.append(f"{probe_id}: mutation setup failed: {exc}")
                continue
            result = run_command(copy_root, probe["validator_command"])
            if result.returncode == 0:
                failures.append(f"{probe_id}: expected validator failure but command exited 0: {probe['validator_command']}")
            else:
                first_line = (result.stdout or "").splitlines()[:1]
                print(f"{probe_id}: expected failure observed via {probe['validator_command']}" + (f" ({first_line[0]})" if first_line else ""))
    skipped = [p for p in manifest.get("probes", []) if p.get("phase") == "post_implementation"]
    for probe in skipped:
        print(f"{probe['id']}: skipped until implementation exists ({probe.get('proof_policy', 'post-implementation only')})")
    print(f"mutation probes executed: {len(executable)}")
    print(f"errors: {len(failures)}")
    if failures:
        for item in failures:
            print(f"- {item}")
        sys.exit(1)


if __name__ == "__main__":
    main()
