from __future__ import annotations
import argparse, dataclasses, importlib, inspect, json, subprocess, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_import(import_path: str):
    module_name, attr_name = import_path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def documented_param_names(signature: str) -> list[str]:
    if '(' not in signature or ')' not in signature:
        return []
    inner = signature.split('(', 1)[1].rsplit(')', 1)[0]
    if not inner.strip():
        return []
    names = []
    depth = 0
    current = []
    for ch in inner:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            part = ''.join(current).strip()
            current = []
            if part:
                names.append(part)
        else:
            current.append(ch)
    tail = ''.join(current).strip()
    if tail:
        names.append(tail)
    cleaned = []
    for part in names:
        part = part.split('=', 1)[0].split(':', 1)[0].strip()
        if part not in {'self', 'cls', '*', '/', '**fields', '...'} and part:
            cleaned.append(part.lstrip('*'))
    return cleaned


def implemented_param_names(obj) -> set[str]:
    try:
        sig = inspect.signature(obj)
    except (TypeError, ValueError):
        return set()
    return {name for name in sig.parameters if name not in {'self', 'cls'} and sig.parameters[name].kind not in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}}


def public_model_fields(obj) -> set[str]:
    fields: set[str] = set()
    if dataclasses.is_dataclass(obj):
        fields.update(f.name for f in dataclasses.fields(obj))
    fields.update(getattr(obj, 'model_fields', {}).keys())
    fields.update(getattr(obj, '__fields__', {}).keys())
    fields.update(getattr(obj, '__annotations__', {}).keys())
    try:
        fields.update(implemented_param_names(obj))
    except Exception:
        pass
    return fields


def validate_schema_paths(errors: list[str], contract: dict) -> None:
    for _, path in (contract.get('source_of_truth') or {}).items():
        p = ROOT / path
        if not p.is_file():
            errors.append(f"source_of_truth path missing: {path}")
        elif p.suffix == '.json':
            try:
                load_json(p)
            except Exception as exc:
                errors.append(f"source_of_truth JSON invalid: {path}: {exc}")


def run_examples(errors: list[str]) -> None:
    result = subprocess.run([sys.executable, '-m', 'pytest', 'examples', '-q'], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        errors.append('pytest examples/ -q failed:\n' + result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--contract', default='docs/contracts/api-contract.yaml')
    parser.add_argument('--run-examples', action='store_true')
    args = parser.parse_args()
    contract = load_yaml(ROOT / args.contract)
    errors: list[str] = []
    validate_schema_paths(errors, contract)
    for entry in contract.get('public_api', []):
        api_id = entry.get('id')
        try:
            obj = resolve_import(entry['import_path'])
        except Exception as exc:
            errors.append(f"{api_id}: import_path does not resolve: {entry.get('import_path')}: {exc}")
            continue
        kind = entry.get('kind')
        if kind == 'function':
            if not callable(obj):
                errors.append(f"{api_id}: expected callable function")
            documented = set(documented_param_names(entry.get('signature', '')))
            implemented = implemented_param_names(obj)
            missing = documented - implemented
            if missing:
                errors.append(f"{api_id}: implementation signature missing documented params: {sorted(missing)}")
        elif kind in {'class', 'dataclass_or_model'}:
            if not inspect.isclass(obj):
                errors.append(f"{api_id}: expected class/model")
            documented = {f.get('name') for f in entry.get('fields', []) if f.get('name')}
            if documented:
                implemented = public_model_fields(obj)
                missing = documented - implemented
                if missing:
                    errors.append(f"{api_id}: implementation model surface missing documented fields/constructor params: {sorted(missing)}")
        elif kind == 'exception':
            if not inspect.isclass(obj) or not issubclass(obj, Exception):
                errors.append(f"{api_id}: expected exception class subclassing Exception")
    if args.run_examples:
        run_examples(errors)
    print(f"api contract entries checked: {len(contract.get('public_api', []))}")
    print(f"examples_executed: {bool(args.run_examples)}")
    print(f"errors: {len(errors)}")
    if errors:
        for error in errors:
            print(f"- {error}")
        sys.exit(1)

if __name__ == '__main__':
    main()
