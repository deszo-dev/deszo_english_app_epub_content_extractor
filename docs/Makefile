.PHONY: validate-docs-static validate-docs-paths validate-manifest-hashes validate-examples-metadata validate-contract-shape validate-mutation-probes run-mutation-probes docs-html serve-docs validate-against-implementation

validate-docs-static:
	python tools/validate_static_docs_package.py

validate-docs-paths:
	python tools/validate_markdown_paths.py

validate-manifest-hashes:
	python tools/validate_manifest_hashes.py

validate-examples-metadata:
	python tools/validate_examples_metadata.py

validate-contract-shape:
	python tools/validate_contract_shape.py

validate-mutation-probes:
	python tools/validate_mutation_probe_manifest.py

run-mutation-probes:
	python -u tools/run_mutation_probes.py

docs-html:
	mkdocs build --strict

serve-docs:
	mkdocs serve

validate-against-implementation:
	python tools/validate_against_implementation.py --contract docs/contracts/api-contract.yaml
