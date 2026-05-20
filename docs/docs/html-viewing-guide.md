# HTML Viewing Guide

## Option A — local live preview

```bash
python -m venv .venv
. .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows PowerShell
pip install -r requirements-docs.txt
mkdocs serve
```

Open:

```text
http://127.0.0.1:8000
```

## Option B — build static HTML

```bash
pip install -r requirements-docs.txt
mkdocs build --strict
```

Open:

```text
site/index.html
```

## Option C — serve already built static HTML

```bash
python -m http.server 8000 --directory site
```

Open:

```text
http://127.0.0.1:8000
```

## Validation before viewing

```bash
make validate-docs-static
make docs-html
```

If the final implementation package does not exist yet, do not run `make validate-against-implementation`.
