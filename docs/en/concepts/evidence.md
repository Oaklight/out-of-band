# Evidence

[English](evidence.md) | [中文](../../zh/concepts/evidence.md)

Evidence is whatever the operator wants to stand behind: logs, measurements, a
test report, a model hash. The receipt does not contain it. The receipt commits
to a digest of the directory, and the archive travels separately.

## The digest

`oob sign --evidence-dir` walks the directory, hashes every regular file, and
builds one manifest line per file:

```text
<sha256 of the file>  <path relative to the directory>
```

The lines are sorted by path, and the digest is the SHA-256 of the manifest.
File modes, ownership, and timestamps do not participate.

An empty directory is valid. Its digest is the SHA-256 of an empty byte string.

Symlinks and special files are rejected. Paths must be UTF-8 and must not
contain `.` or `..` components, LF, CR, or NUL. Skipping a bad path would let
two different trees produce the same digest, so the operation fails instead.

## Pack the archive

```bash
oob pack --evidence-dir ./evidence --out evidence.tgz
```

`oob pack` writes a deterministic `.tar.gz` with sorted entries and zeroed
metadata, then prints the file count and digest. Unpacking it reproduces the
digest that `oob sign` recorded. Repacking is safe; changing a file is not.

## Send it to the verifier

There are three sources, tried in this order:

1. `evidence-file`: a path on the runner.
2. `evidence-url`: an HTTPS URL.
3. `claims.evidence_url`: a URL signed into the receipt.

The first one exists so a caller that already has the archive (a previous step,
an artifact download) can hand it over directly. The second and third cover a
machine that cannot reach the runner.

The transport does not need to be trusted. The verifier extracts the archive,
recomputes the digest, and compares it with the signed value. A mismatch is
`E_EVIDENCE_MISMATCH`, which makes the verdict `unverified`, never a pass.

A URL must be reachable from the GitHub runner. A private object store needs a
signed URL. The GitHub token is sent only to `api.github.com` and `github.com`;
every other host must serve the archive publicly or with its own signature.

## Required by default

The action and the reusable workflow require evidence by default. Supply an
archive through one of the three sources, or set `require-evidence: false`.

| Situation | Verdict |
| --- | --- |
| archive supplied and digest matches | `verified` or `failed`, depending on `result` |
| no archive supplied | `unverified`, `E_NO_EVIDENCE` |
| archive supplied but digest differs | `unverified`, `E_EVIDENCE_MISMATCH` |
| `require-evidence: false`, no archive | verdict from the receipt; summary says `digest only` |

When evidence is required, an archive that cannot be read or extracted also
makes the verdict `unverified`. There is no silent fallback.

## What the run shows

A matching archive is uploaded as the `oob-evidence` artifact. The job summary
gets a manifest table (file, bytes, short SHA-256) and a folded preview of up
to 20 text files, capped at 32 KiB per file and 256 KiB in total. Binary files
are listed but not previewed. The rest stays in the artifact.

Artifacts and run summaries follow Actions retention: 90 days by default, and
a public repository can only lower it. The receipt in the pull request comment
is the durable record. If the evidence itself must remain verifiable later,
host it somewhere you control and record the location in
`claims.evidence_url`.

## Hosting choices

Any of these works; pick what your environment already has:

- a branch in the same repository, for example `evidence/<sha>`;
- a release asset;
- an object store with a signed URL;
- a gist or another public paste for a small text archive;
- an internal share reachable from the runner.

The archive is visible to anyone who can read the run or the URL. Treat it like
a CI log: do not include secrets, tokens, customer data, or private keys.

## Limits

| Limit | Value |
| --- | --- |
| Archive size | 50 MiB |
| Files | 1000 |
| Manifest entries | one per regular file |
| Preview per file | 32 KiB |
| Preview total | 256 KiB |
| Previewed files | 20 |

Archive extraction rejects absolute paths, `..`, links, and special files
before writing anything.

## Errors

| Code | Meaning |
| --- | --- |
| `E_NO_EVIDENCE` | evidence was required and no source produced an archive |
| `E_EVIDENCE_MISMATCH` | the archive does not hash to the signed digest |
| `E_EVIDENCE_ARCHIVE` | the archive is unsafe or unreadable |
| `E_EVIDENCE_PATH` | a filename is not UTF-8 or contains LF, CR, or NUL |
| `E_EVIDENCE_TYPE` | the directory contains a symlink or special file |
| `E_KEY_IN_EVIDENCE` | the private key is inside the directory being signed |

The full table is in [CLI](../reference/cli.md#error-codes).
