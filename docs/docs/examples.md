# Examples

Executable contract examples live in the root `examples/` directory and are indexed by `docs/contracts/examples-manifest.json`.

Examples are designed for two phases:

- static docs review: examples must exist, parse as Python, import only public API, and contain assertions;
- post-implementation: examples should run with `pytest examples/ -q` after the package exists.

| File | Purpose |
|---|---|
| `examples/how_to_start.py` | Minimal extraction call with generated EPUB input. |
| `examples/public_api_examples.py` | Config model, extraction result, and canonical text builder. |
| `examples/batch_usage.py` | Batch-style repeated extraction using public API only. |
| `examples/error_handling.py` | Structured failed results and programmer-error handling. |
