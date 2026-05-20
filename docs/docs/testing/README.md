# Testing Fixtures

This directory contains contract fixtures and expected normalized outputs for post-implementation tests.

- `fixtures/input/` contains deterministic source specs used to generate runtime EPUB or invalid archive inputs.
- `fixtures/config/` contains per-fixture config JSON.
- `fixtures/expected/` contains normalized expected result JSON.
- `goldens/` is reserved for accepted generated outputs after implementation proof.

All fixture files are pinned by `docs/contracts/fixture-manifest.json`.
