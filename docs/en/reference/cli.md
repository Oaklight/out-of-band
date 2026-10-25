# CLI

[English](cli.md) | [中文](../../zh/reference/cli.md)

```text
oob sign   --job <name> --commit <sha> --result pass|fail
                --evidence-dir <dir> --key <path>
                [--repo <owner/name>] [--claims k=v ...]
                [--output-file <file>] [--allow-dirty] [--out <file>]

oob pack   --evidence-dir <dir> --out <file> [--json]

oob verify --block <file> --allowed-signers <file>
                --repo <owner/name> --commit <sha> --expect-job <name>
                [--expect-tree <sha>] [--json]

oob render --block <file|-> [--out <file>]
```

Every command exits `0` on success. `verify` uses exits `1` and `2` for
verdicts; everything else uses `3` for a tool error.

## `oob sign`

Produces a receipt block for one commit.

| Flag | Required | Meaning |
| --- | --- | --- |
| `--job` | yes | job name the consumer expects |
| `--commit` | yes | full 40-hex commit that exists locally |
| `--result` | yes | `pass` or `fail` |
| `--evidence-dir` | yes | directory to hash for the evidence digest |
| `--key` | yes | private key path |
| `--repo` | no | `owner/name`; defaults to the `origin` remote |
| `--claims` | no | `k=v`, repeatable |
| `--output-file` | no | up to 4096 bytes of curated output; emits schema v2 |
| `--allow-dirty` | no | sign with uncommitted changes |
| `--out` | no | write the block to a file instead of stdout |

Rules worth knowing:

- `--commit` must be a full SHA, not a branch or a short form. The tree comes
  from the commit object, not from the worktree.
- The key must not be inside the evidence directory.
- `--claims` values are parsed as JSON when they are valid scalars or arrays of
  the allowed shapes; otherwise they are strings. Floats, null, and integers
  outside the safe JSON range are rejected.
- The output is the block only. Status messages go to stderr.
- No network access and no GitHub credential are used.

## `oob pack`

Writes a deterministic `.tar.gz` of the evidence directory.

| Flag | Meaning |
| --- | --- |
| `--evidence-dir` | directory to pack |
| `--out` | archive path |
| `--json` | print `{"count":N,"digest":"sha256:..."}` |

The digest is the same one `oob sign` records. Packing after signing is fine as
long as the contents do not change.

## `oob verify`

Checks a block against a trust root and an expected context.

| Flag | Required | Meaning |
| --- | --- | --- |
| `--block` | yes | file holding the marker and both fences |
| `--allowed-signers` | yes | OpenSSH allowed-signers file |
| `--repo` | yes | expected `owner/name`, compared case-insensitively |
| `--commit` | yes | expected commit, compared case-insensitively |
| `--expect-job` | yes | expected job, compared exactly |
| `--expect-tree` | no | expected tree, compared case-insensitively |
| `--json` | no | print one machine-readable line |

Human output is a short summary. With `--json`, the line is:

```json
{"verdict":"pass|fail|unverified|error","code":"OK|E_...","repo":null,"commit":null,"job":null}
```

`repo`, `commit`, and `job` stay `null` unless the receipt parsed and its
signature verified. Before that, the values are attacker-controlled.

The exit code is authoritative:

| Exit | Meaning |
| --- | --- |
| 0 | valid receipt with `result: pass` |
| 1 | valid receipt with `result: fail` |
| 2 | no receipt, or a receipt that does not verify |
| 3 | usage or internal error |

## `oob render`

Turns a block into a Markdown comment: a table of signed fields and claims, the
optional output, and the exact block inside a collapsed `<details>` section.

| Flag | Meaning |
| --- | --- |
| `--block` | input file, or `-` for stdin |
| `--out` | write the comment to a file instead of stdout |

The table is presentation. Verification reads only the block, so rendering
never changes the signed bytes.

## Exit codes

| Exit | Meaning |
| --- | --- |
| 0 | success; for `verify`, a valid `pass` |
| 1 | `verify` only: a valid receipt that says `fail` |
| 2 | `verify` only: absent or invalid receipt |
| 3 | usage, I/O, or internal error; no receipt was produced |

A missing receipt is exit 2, never 0. The CI verifier maps exit 2 to
`unverified` with a `failure` conclusion.

## Error codes

Printed as `error: <CODE>: <message>` on stderr.

| Code | Meaning | Exit |
| --- | --- | --- |
| `OK` | verification succeeded (`pass` or valid `fail`) | 0 or 1 |
| `E_NO_BLOCK` | no receipt marker found | 2 |
| `E_MULTI_BLOCK` | more than one marker, or trusted comments that disagree | 2 |
| `E_TOO_LARGE` | block exceeds 16 KiB | 2 |
| `E_BAD_FENCE` | fences missing or in the wrong order | 2 |
| `E_MULTI_LINE` | JSON payload is not one line | 2 |
| `E_BAD_JSON` | not valid UTF-8 or not JSON | 2 |
| `E_DUP_KEY` | duplicate JSON object key | 2 |
| `E_UNKNOWN_FIELD` | field not defined by the schema version | 2 |
| `E_BAD_SCHEMA` | `schema` is not a supported receipt version | 2 |
| `E_BAD_TYPE` | wrong JSON type, float, or null | 2 |
| `E_BAD_VALUE` | value violates its pattern or range | 2 |
| `E_CLAIMS_LIMIT` | claims exceed count, size, or shape limits | 2 |
| `E_OUTPUT_LIMIT` | `output` exceeds 4096 bytes | 2 or 3 |
| `E_EVIDENCE_ARCHIVE` | evidence archive is unsafe or unreadable | 2 |
| `E_EVIDENCE_MISMATCH` | uploaded evidence does not match the signed digest | 2 |
| `E_NO_EVIDENCE` | a required evidence archive was not supplied | 2 |
| `E_BAD_SIGNATURE` | signature armor is malformed | 2 |
| `E_NO_PRINCIPAL` | no principal in `allowed_signers` accepts the signature | 2 |
| `E_WRONG_REPO` | `repo` does not match the expected repository | 2 |
| `E_WRONG_COMMIT` | `commit` does not match the expected head | 2 |
| `E_WRONG_TREE` | `tree` does not match the expected tree | 2 |
| `E_WRONG_JOB` | `job` does not match the expected job name | 2 |
| `E_BAD_ALLOWED_SIGNERS` | file missing, no keys, or a wildcard principal | 3 |
| `E_TOO_MANY_COMMENTS` | more than 5000 comments to scan | 3 |
| `E_KEY_IN_EVIDENCE` | signing key is inside the evidence directory | 3 |
| `E_NOT_A_REPO` | `sign` was run outside a git repository | 3 |
| `E_NO_REMOTE` | no `origin` remote and no `--repo` | 3 |
| `E_UNKNOWN_COMMIT` | the commit does not exist locally | 3 |
| `E_SIGN_FAILED` | `ssh-keygen` could not produce a signature | 3 |
| `E_DIRTY_WORKTREE` | uncommitted changes without `--allow-dirty` | 3 |
| `E_EVIDENCE_PATH` | a filename is not UTF-8 or contains LF, CR, or NUL | 3 |
| `E_EVIDENCE_TYPE` | evidence contains a symlink or non-regular file | 3 |
| `E_EVIDENCE_READ` | evidence directory is missing or unreadable | 3 |
| `E_USAGE` | invalid command line | 3 |
| `E_INTERNAL` | unexpected failure | 3 |

Codes with exit 2 mean a receipt was found and rejected, except `E_NO_BLOCK`,
which means none was found.

## Not in the CLI

There is no `publish` command. Creating a check run needs a GitHub App
identity. Inside Actions, `GITHUB_TOKEN` is the Actions App, so publishing lives
in the workflow or action. A personal access token can create commit statuses,
not check runs, and a status is not this gate.

## Debugging

`OOB_DEBUG=1` makes an unexpected failure print a traceback. Without it, the
CLI prints `error: E_INTERNAL: ...` and exits 3.
