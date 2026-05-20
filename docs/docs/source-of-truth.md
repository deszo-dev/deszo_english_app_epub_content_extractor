# Source of Truth

| Area | Canonical artifact | Generated / derived artifacts | Validation gate |
|---|---|---|---|
| Public API | `docs/contracts/api-contract.yaml` | `docs/public-api.md`, `docs/api/*.md`, `examples/*.py` | `tools/validate_contract_shape.py` |
| Human docs | `docs/**/*.md` listed in `docs/contracts/docs-manifest.json` | HTML in `site/` | `tools/validate_static_docs_package.py` |
| Examples | `examples/*.py` + `docs/contracts/examples-manifest.json` | Embedded snippets in docs | `tools/validate_examples_metadata.py` |
| Schemas | `docs/schemas/*.json` | Validation reports | `tools/validate_static_docs_package.py` |
| Diagnostics | `docs/contracts/diagnostics-registry.json` | `docs/diagnostics.md` | `tools/validate_static_docs_package.py` |
| Fixtures / expected outputs | `docs/testing/**` + `docs/contracts/fixture-manifest.json` | testing guide references | `tools/validate_manifest_hashes.py` |
| Fixture-to-test coverage | `docs/contracts/test-coverage-manifest.json` | `docs/testing-guide.md` tables and generated pytest suites | `tools/validate_static_docs_package.py` |
| Archive security policy | `docs/security-archive-policy.md` | security fixtures and mutation probes | `tools/validate_static_docs_package.py` |
| Mutation proof | `docs/contracts/mutation-probes.json` | isolated temp-copy mutation runs | `tools/run_mutation_probes.py` |
| HTML | `mkdocs.yml` + `docs/**/*.md` | `site/index.html` | `mkdocs build --strict` |
| Implementation conformance | docs contracts + code package | post-implementation report | `tools/validate_against_implementation.py` |

## Critical rule

The absence of final implementation code does not reduce the documentation readiness score. Implementation conformance is a separate post-implementation gate.

## Precedence

1. `docs/contracts/api-contract.yaml` for public Python API.
2. JSON Schemas under `docs/schemas/` for config/result/options shapes.
3. Registries under `docs/contracts/` for diagnostics and structured errors.
4. Human Markdown docs for rationale, usage, examples, and validation process.
5. `examples/*.py` for executable contract examples.
6. `docs/contracts/test-coverage-manifest.json` for fixture-to-test traceability.
7. `docs/security-archive-policy.md` for archive validation precedence and exact security predicates.
