# Archive Security Policy

This page is normative for archive handling in `epub_content_extractor`. It closes the security edge-case contract that is only summarized in the configuration and input/output pages.

## Security validation precedence

Archive security validation MUST run before OPF/container/package discovery. If the same file has both an archive security violation and a missing/unreadable OPF package document, the extractor MUST return the archive security error first.

Required failure error:

```text
epub_archive_security_violation
```

The extractor MUST NOT emit a partial `book` object after an archive security failure.

## Compression ratio policy

For each ZIP entry with `compressed_size > 0`:

```text
entry_compression_ratio = uncompressed_size / compressed_size
```

For entries with `compressed_size == 0`:

```text
entry_compression_ratio = 0        when uncompressed_size == 0
entry_compression_ratio = infinity when uncompressed_size > 0
```

Validation fails with `epub_archive_security_violation` if any entry ratio is greater than `max_archive_compression_ratio`.

Aggregate archive size is checked independently:

```text
aggregate_uncompressed_bytes = sum(entry.uncompressed_size for every archive entry)
```

Validation fails with `epub_archive_security_violation` if `aggregate_uncompressed_bytes > max_archive_uncompressed_bytes`.

## Entry count policy

```text
archive_entry_count = number of ZIP central-directory entries
```

Validation fails with `epub_archive_security_violation` if `archive_entry_count > max_archive_entry_count`.

## Path traversal and absolute path policy

Every ZIP entry name MUST be normalized with POSIX path semantics before use. The extractor MUST reject entries that match any of these predicates:

| Predicate | Example | Required error |
|---|---|---|
| Contains a parent traversal segment after normalization | `OPS/../evil.xhtml` | `epub_archive_security_violation` |
| Escapes the intended extraction root | `../../evil.xhtml` | `epub_archive_security_violation` |
| Starts with a POSIX root | `/OPS/chapter.xhtml` | `epub_archive_security_violation` |
| Starts with a Windows drive or UNC-like root | `C:/evil.xhtml`, `//server/share` | `epub_archive_security_violation` |
| Contains an empty normalized name | `.` or empty name | `epub_archive_security_violation` |

No archive entry may be written outside a temporary extraction root. Implementations MAY avoid physical extraction entirely, but the same path policy still applies.

## Symlink and special file policy

If the ZIP metadata exposes an entry as a symbolic link, device, FIFO, socket, or other non-regular file, the extractor MUST reject it with `epub_archive_security_violation`. Only regular files and directory entries are permitted.

## Duplicate entry policy

Duplicate normalized archive entry names are ambiguous. The extractor MUST reject duplicates with `epub_archive_security_violation` rather than choosing first-wins or last-wins behavior.

## Malformed archive policy

Malformed ZIP central directory, unreadable local file headers, encrypted entries, or unsupported compression methods MUST produce a structured failed result. Use the most specific error from `docs/contracts/error-registry.json`; if the malformed archive also violates a security predicate above, `epub_archive_security_violation` wins.

## Fixture and test coverage

The current fixture-backed security proof is:

- `docs/testing/fixtures/input/security_path_traversal.fixture.json`
- `docs/testing/fixtures/config/security_path_traversal.config.json`
- `docs/testing/fixtures/expected/security_path_traversal.expected.normalized.json`

Additional archive security fixtures SHOULD be added for compression-ratio overflow, aggregate uncompressed-size overflow, entry-count overflow, absolute POSIX path, Windows drive path, symlink entry, duplicate normalized path, malformed central directory, encrypted entry, and unsupported compression method.

All archive security fixtures MUST be mapped through `docs/contracts/test-coverage-manifest.json` before they are treated as release-blocking tests.
