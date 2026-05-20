# epub_content_extractor Contract-First Documentation Package

This archive contains contract-first documentation for the `epub_content_extractor` Python module.

The documentation is the source of truth. The implementation package is not required for static documentation review.

## View HTML documentation

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

Open `http://127.0.0.1:8000`.

## Build static HTML

```bash
mkdocs build --strict
python -m http.server 8000 --directory site
```

## Validate static documentation package

```bash
make validate-docs-static
make validate-docs-paths
make validate-manifest-hashes
make validate-examples-metadata
make validate-contract-shape
make validate-mutation-probes
make run-mutation-probes
make docs-html
```

## Validate implementation later

Run this only after the Python module implementation exists:

```bash
make validate-against-implementation
pytest examples/ -q
```

## Static review rule

The absence of final implementation code does not reduce the documentation readiness score. Implementation conformance is a separate post-implementation gate.

## Run mutation probes

Executable static mutation probes run in isolated temporary copies and prove that the static validators catch expected drift classes:

```bash
make run-mutation-probes
```

Post-implementation probes are listed but skipped until implementation exists.
