# Validation Guide

## Static documentation validation

Static validation does not import the target implementation package.

```bash
make validate-docs-static
```

Expected output shape:

```text
static documentation package validation complete
normative_markdown_files: <N>
schemas: <N>
api_contract_entries: <N>
examples: <N>
fixtures: <N>
goldens: <N>
diagnostics: <N>
mutation_probes: <N>
missing_paths: 0
errors: 0
```

## Individual gates

```bash
make validate-docs-paths
make validate-manifest-hashes
make validate-examples-metadata
make validate-contract-shape
make validate-mutation-probes
```

## HTML build gate

```bash
make docs-html
```

Install `requirements-docs.txt` first.

## Post-implementation gate

Run only after the package implementation exists:

```bash
make validate-against-implementation
pytest examples/ -q
```


## Mutation probe proof

Run executable static mutation probes in an isolated temporary copy:

```bash
make run-mutation-probes
```

Post-implementation mutation probes are listed in `docs/contracts/mutation-probes.json`, but are skipped until implementation code exists.
