# Compatibility and Versioning

The implementation package uses SemVer. The result/config contracts use explicit schema versions.

## Breaking changes

The following require at least a new schema version and usually a major implementation version:

- changing `schema_version` semantics;
- removing, renaming, or changing field type/nullability;
- changing required/optional field presence;
- changing diagnostic severity;
- removing or renaming diagnostic/error codes;
- changing CLI exit-code meaning;
- changing `extract_epub_content()` or `build_canonical_text()` signatures;
- changing config defaults or hard bounds.

## Non-breaking changes

The following can be non-breaking if fixture outputs remain valid:

- implementation refactoring;
- performance improvements;
- changing non-stable human diagnostic messages;
- adding implementation-specific debug subfields when `include_debug = true`.
