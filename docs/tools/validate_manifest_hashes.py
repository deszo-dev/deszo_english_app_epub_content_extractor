from __future__ import annotations
import ast, hashlib, inspect, json, os, re, sys
from pathlib import Path
try:
    import yaml
except Exception:
    yaml = None
ROOT = Path(__file__).resolve().parents[1]
def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))
def load_yaml(path: str):
    if yaml is None:
        raise RuntimeError("PyYAML is required")
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
def require_file(errors, path: str):
    p = ROOT / path
    if not p.exists() or not p.is_file():
        errors.append(f"missing file: {path}")
    return p
def parse_python(path: Path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
def has_assert(tree: ast.AST) -> bool:
    return any(isinstance(node, ast.Assert) for node in ast.walk(tree))
def imported_modules(tree: ast.AST):
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names
def markdown_links(text: str):
    for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        yield match.group(1).split()[0].strip("<>")
def strip_code_fences(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)

def main():
    errors=[]
    manifest=load_json("docs/contracts/fixture-manifest.json")
    count=0
    for fixture in manifest.get("fixtures",[]):
        for info in fixture.get("files",[]):
            p=require_file(errors, info.get("path"))
            if p.exists():
                count += 1
                if p.stat().st_size != info.get("bytes"):
                    errors.append(f"byte count mismatch: {info.get('path')}")
                if sha256_file(p) != info.get("sha256"):
                    errors.append(f"sha256 mismatch: {info.get('path')}")
    print(f"fixture files checked: {count}")
    print(f"errors: {len(errors)}")
    if errors:
        for e in errors: print(f"- {e}")
        sys.exit(1)
if __name__ == "__main__":
    main()
