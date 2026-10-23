# Outboard SPEC — v0.1

Status: normative for `v0.1.x`. Mechanism only.

Outboard lets a job run where GitHub cannot reach it, sign a receipt bound to a
commit, and have a hosted workflow verify that receipt and publish the verdict
as a check.

This document pins the schema, the verification order, the evidence digest, the
exit codes, and the workflow contract. Anything not pinned here is not part of
v0.1.

## 0. Boundary

| Layer | Contents | Lives in |
|---|---|---|
| Mechanism | receipt format, signing, verification, check publishing, sticky comment, step summary | this repository |
| Policy | which paths require a receipt, what the check runs, which key, required vs optional | the consumer repository |

If the words `gpu`, `sm70`, or `patches/` appear in this repository, the split is
broken. Outboard knows nothing about what the job does.

**Non-goals for v0.1:** no runner, no hosted service, no GitHub App, no Sigstore,
no scheduler, no artifact storage, no CLI command that publishes a check.

## 1. Receipt block

### 1.1 Envelope

A receipt is an HTML comment marker followed by exactly two fenced blocks:

````text
<!-- receipt:v1 -->
```json
{"schema":"receipt/v1","repo":"OWNER/NAME","commit":"<40 hex>","tree":"<40 hex>","job":"smoke","result":"pass","issued_at":"2026-10-23T21:40:00Z","tool":"outboard/0.1.0","evidence":{"count":7,"digest":"sha256:<64 hex>"},"claims":{"device_count":2}}
```
```ssh-signature
-----BEGIN SSH SIGNATURE-----
...
-----END SSH SIGNATURE-----
```
````

Rules:

- The marker `<!-- receipt:v1 -->` appears at most once per comment. Zero
  occurrences means "no receipt" (exit 2). More than one means invalid (exit 2).
- The JSON block is exactly one line. The signature covers the literal bytes of
  that line, excluding the line terminator and both fences. It never covers a
  re-serialized object.
- The `json` and `ssh-signature` fences are lowercase and exact. Blank lines
  between blocks are allowed; anything else between them is invalid.
- Text outside the block is ignored. The envelope is still parsed strictly.
- A comment that carries the marker but a malformed envelope is **invalid**, not
  absent. The two states are reported differently (see §4).

### 1.2 JSON object

Exactly these top-level fields. Unknown fields are rejected, not ignored.

| Field | Type | Required | Rule |
|---|---|---|---|
| `schema` | string | yes | exactly `receipt/v1` |
| `repo` | string | yes | `owner/name`, one `/`, 3–140 bytes, no whitespace |
| `commit` | string | yes | 40 hex; emitted lowercase, compared case-insensitively |
| `tree` | string | yes | 40 hex; emitted lowercase |
| `job` | string | yes | `[A-Za-z0-9][A-Za-z0-9._-]{0,63}` |
| `result` | string | yes | `pass` or `fail` |
| `issued_at` | string | yes | `YYYY-MM-DDTHH:MM:SSZ`, UTC, second precision |
| `tool` | string | yes | `outboard/<semver>`; informational, never trusted |
| `evidence` | object | yes | see below |
| `evidence.count` | integer | yes | 0–1,000,000; no floats |
| `evidence.digest` | string | yes | `sha256:` + 64 lowercase hex |
| `claims` | object | no | defaults to `{}`; rules in §1.2.1 |

No other top-level fields. No nested objects other than `evidence` and `claims`.
No floats anywhere. No `null` values.

The signer emits fields in the order above with compact separators (`","` and
`":"`). A verifier must not require that order, because the signature is over
the bytes as written.

#### 1.2.1 Claims

`claims` carries consumer-defined facts that are safe to show in public.

- Key: `[a-z][a-z0-9_.-]{0,63}`.
- Value: string (≤ 256 bytes, no control characters), integer (signed 64-bit),
  boolean, or an array of at most 16 of those scalars. No nested objects, no
  arrays of arrays, no floats.
- The serialized `claims` object is at most 2048 bytes.
- Claims are data. They are displayed in the check summary and must never be
  interpreted as instructions.

### 1.3 Size limits

- The whole block (marker through the final fence) is at most **16 KiB** of
  UTF-8. Reject before parsing.
- A comment containing more than one marker is rejected before any JSON parse.

### 1.4 Extraction from a comment

A verifier given a comment body:

1. Count marker occurrences. 0 → absent; ≥ 2 → invalid.
2. Find the first ```` ```json ```` after the marker. The next line is the JSON
   payload. The line after it must be ```` ``` ````. Otherwise invalid.
3. Skip blank lines. Find ```` ```ssh-signature ````. Everything up to the next
   ```` ``` ```` is the signature.
4. If any step fails, the block is invalid.

Trailing content after the signature fence is ignored.

When the receipt is collected from PR comments (workflow mode, §6.4), the
workflow considers at most the newest 1000 comments. If no marker is found, the
receipt is absent. If several comments carry blocks: byte-identical blocks are
accepted as one; any two that differ make the receipt invalid.

## 2. Evidence digest

The evidence directory is never uploaded. The receipt commits to it so the
operator can reproduce it later.

### 2.1 Algorithm

1. Walk the directory recursively. Include every regular file, including
   dotfiles and files in subdirectories.
2. Reject the whole operation on any symlink, FIFO, socket, or device file.
   Do not follow symlinks.
3. For each file, compute `sha256` over its raw bytes.
4. Build one manifest line per file:

   ```text
   <64 lowercase hex><SPACE><SPACE><relative path><LF>
   ```

5. Paths are relative to the evidence directory, use `/` as the separator, and
   never contain `.` or `..` components.
6. Sort lines by the unsigned byte order of the UTF-8 encoded path.
7. `digest = "sha256:" + hex(sha256(manifest bytes))`.
8. `count` is the number of files.

An empty directory is valid: `count` is 0 and the digest is the SHA-256 of the
empty byte string,
`sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

File modes, ownership, and timestamps are not part of the digest.

### 2.2 Signer-side rules

- The private key must not live inside the evidence directory. Refuse with
  `E_KEY_IN_EVIDENCE`.
- The evidence directory and the key path are never written into the receipt.

## 3. Verification

### 3.1 Order

Verification runs these steps in order and stops at the first failure:

1. **Size.** More than 16 KiB → `E_TOO_LARGE`.
2. **Envelope.** Marker count, fences, single-line JSON → `E_NO_BLOCK`,
   `E_MULTI_BLOCK`, `E_BAD_FENCE`, `E_MULTI_LINE`.
3. **JSON parse.** UTF-8, one object, no duplicate keys, no floats, no null →
   `E_BAD_JSON`, `E_DUP_KEY`, `E_BAD_TYPE`.
4. **Schema.** Version, field set, types, value patterns, claims limits →
   `E_BAD_SCHEMA`, `E_UNKNOWN_FIELD`, `E_BAD_VALUE`, `E_CLAIMS_LIMIT`.
5. **Signature.** Over the literal JSON bytes, namespace `receipt`, against the
   keys in `allowed_signers` → `E_BAD_SIGNATURE`, `E_NO_PRINCIPAL`,
   `E_BAD_ALLOWED_SIGNERS`.
6. **Bindings.** `repo` (case-insensitive), `commit` (case-insensitive),
   `job` (exact), and `tree` only when the caller passes `--expect-tree` →
   `E_WRONG_REPO`, `E_WRONG_COMMIT`, `E_WRONG_JOB`, `E_WRONG_TREE`.
7. **Result.** `pass` → exit 0; `fail` → exit 1.

Cheap checks come first so a hostile comment cannot make the verifier do work.
Bindings are checked after the signature because before that, their values are
attacker-controlled.

### 3.2 Signature

- `ssh-keygen -Y verify -f <allowed_signers> -I <principal> -n receipt -s <sig>`
  with the literal JSON line on stdin.
- `allowed_signers` is the standard OpenSSH format:
  `principal [options] keytype base64 [comment]`.
- The verifier parses the file itself and tries each distinct principal. A
  signature is valid if any principal accepts it. No match → `E_NO_PRINCIPAL`.
- Wildcard principals (`*`, `?`, `!`) are rejected with `E_BAD_ALLOWED_SIGNERS`.
- The namespace is `receipt`. A signature made under any other namespace fails.
- `ssh-keygen`'s exit status is the only signal used. Text it prints about the
  matching key is not parsed.

## 4. Exit codes and error codes

### 4.1 Exit codes

| Meaning | Exit |
|---|---|
| Valid receipt with `result: pass` | 0 |
| Valid receipt with `result: fail` | 1 |
| Absent or invalid receipt | 2 |
| Usage or internal error | 3 |

"Not run" (2) and "ran and failed" (1) are never collapsed. A missing receipt is
unverified, never skipped.

Exit 3 means the tool could not do its job (bad flags, missing file, a bug). It
is not an opinion about the receipt.

### 4.2 Error codes

Stable strings, printed as `error: <CODE>: <message>` on stderr.

| Code | Meaning |
|---|---|
| `OK` | verification succeeded (pass) or produced a valid fail |
| `E_NO_BLOCK` | no receipt marker found |
| `E_MULTI_BLOCK` | more than one marker, or two comments that disagree |
| `E_TOO_LARGE` | block exceeds 16 KiB |
| `E_BAD_FENCE` | fences missing or in the wrong order |
| `E_MULTI_LINE` | JSON payload is not one line |
| `E_BAD_JSON` | not valid UTF-8 or not JSON |
| `E_DUP_KEY` | duplicate JSON object key |
| `E_UNKNOWN_FIELD` | field not defined by this schema |
| `E_BAD_SCHEMA` | `schema` is not `receipt/v1` |
| `E_BAD_TYPE` | wrong JSON type, float, or null |
| `E_BAD_VALUE` | value violates its pattern or range |
| `E_CLAIMS_LIMIT` | claims exceed count, size, or shape limits |
| `E_BAD_SIGNATURE` | signature does not verify |
| `E_NO_PRINCIPAL` | no principal in `allowed_signers` accepts the signature |
| `E_BAD_ALLOWED_SIGNERS` | missing file, no keys, or a wildcard principal |
| `E_WRONG_REPO` | `repo` does not match the expected repository |
| `E_WRONG_COMMIT` | `commit` does not match the expected head |
| `E_WRONG_TREE` | `tree` does not match the expected tree |
| `E_WRONG_JOB` | `job` does not match the expected job name |
| `E_KEY_IN_EVIDENCE` | signing key is inside the evidence directory |
| `E_DIRTY_WORKTREE` | uncommitted changes without `--allow-dirty` |
| `E_EVIDENCE_*` | evidence directory could not be read or contains a symlink |
| `E_USAGE` | invalid command line |
| `E_INTERNAL` | unexpected failure |

## 5. CLI

```
outboard sign   --job <name> --commit <sha> --result pass|fail
                --evidence-dir <dir> --key <path>
                [--repo <owner/name>] [--claims k=v ...]
                [--allow-dirty] [--out <file>]

outboard verify --block <file> --allowed-signers <file>
                --repo <owner/name> --commit <sha> --expect-job <name>
                [--expect-tree <sha>] [--json]
```

### 5.1 `sign`

- `--commit` must be a full 40-hex commit that exists locally
  (`git cat-file -e <sha>^{commit}`). Short SHAs are rejected.
- `tree` is read from the commit, never from the working tree.
- `--repo` defaults to the `origin` remote, parsed from SSH or HTTPS URLs. If it
  cannot be determined unambiguously, `--repo` is required.
- `--claims k=v` may repeat. `v` is parsed as a JSON scalar when possible,
  otherwise as a string. A value may also be a JSON array literal.
- Refuses a dirty worktree with `E_DIRTY_WORKTREE` unless `--allow-dirty`. Even
  then, the receipt binds a commit, so a dirty tree only helps for local
  experiment.
- Writes the block to stdout, or to `--out`.
- No network access, no GitHub credential, no machine identity.

### 5.2 `verify`

- `--block` accepts a file containing the marker and both fences. A bare JSON
  line with a separate signature is not accepted.
- Prints a human summary to stdout. With `--json`, prints exactly one line:
  `{"verdict":"pass|fail|unverified|error","code":"E_...","repo":...,"commit":...,"job":...}`
  and nothing else. The exit code remains authoritative.
- Never executes anything from the receipt. The JSON payload is never passed to
  a shell, `eval`, or a template engine.

### 5.3 Not in v0.1

There is no `publish` command. Creating a check run requires a GitHub App
identity; inside Actions, `GITHUB_TOKEN` is the Actions App, so publishing lives
in the workflow (§6). A PAT can create only commit statuses, which is a different
object and is not this gate.

## 6. Reusable workflow contract

File: `.github/workflows/verify.yml`, triggered by `workflow_call` only.

### 6.1 Inputs

| Input | Type | Default | Meaning |
|---|---|---|---|
| `pr` | string | `"0"` | PR number for comment collection and the sticky comment; `0` disables both |
| `commit` | string | required | expected head SHA; passed to `check-runs` as `head_sha` |
| `job` | string | required | expected `job` value |
| `required` | boolean | `true` | whether this PR needs a receipt |
| `check-name` | string | `outboard` | check run name; this is what branch protection matches |
| `receipt` | string | `""` | receipt text passed directly (dispatch payload); takes precedence over comments |
| `allowed-signers` | string | `.github/allowed_signers` | path in the caller repository, read from the default branch |

### 6.2 Permissions

The caller must grant:

```yaml
permissions:
  contents: read
  checks: write
  pull-requests: write
```

The called workflow uses no repository secrets. `GITHUB_TOKEN` is the only
credential.

### 6.3 Execution rules

1. Check out the caller repository at its **default branch**, with
   `persist-credentials: false`. Never check out or execute PR code.
2. Install `outboard` at an exact version pinned in the workflow file.
3. The only repository file read besides the workflow itself is
   `allowed-signers`.
4. Treat the receipt as data. Cap its size before parsing. Never interpolate it
   into a shell command.
5. Set a job timeout of 5 minutes.

### 6.4 Receipt resolution

- If `receipt` is non-empty, use it.
- Else if `pr` > 0, read the newest 1000 PR comments and apply §1.4 to each.
- Else the receipt is absent.

### 6.5 Outcomes

| `required` | Receipt | Verify exit | Check conclusion | Summary |
|---|---|---|---|---|
| true | absent | 2 | `action_required` | unverified — no receipt |
| true | invalid | 2 | `action_required` | unverified — `<CODE>` |
| true | valid, pass | 0 | `success` | verified |
| true | valid, fail | 1 | `failure` | failed |
| false | any | — | `success` | not applicable — receipt not evaluated |
| — | — | 3 | none; the job fails | tool error |

When `required` is false the receipt is not evaluated at all. A stale failing
receipt must not block a PR the policy already classified as not needing one.

Exit 3 publishes no check. If the check name is required by branch protection,
the merge stays blocked, which is the fail-closed result.

### 6.6 Check run

- `POST /repos/{owner}/{repo}/check-runs` with `name`, `head_sha` = `commit`,
  `status: completed`, the conclusion above, and `output.title` /
  `output.summary` equal to the step summary text.
- A new check run is created per verification. The newest one wins for branch
  protection; older ones remain visible in the Checks tab.
- The check name is public API. Changing it silently changes what branch
  protection enforces.

### 6.7 Sticky comment

- One comment per PR, found by the marker `<!-- outboard:state -->` authored by
  the same app; edited in place with `PATCH /repos/{owner}/{repo}/issues/comments/{id}`.
- Create only when no such comment exists. Never delete or edit another actor's
  comments.
- The body shows: state, job, short commit, `issued_at`, the error code when
  unverified, and the same text as the step summary. No machine identity.
- Callers should set `concurrency` per PR so two runs do not race the same
  comment.

### 6.8 Consumer wiring (example)

```yaml
jobs:
  policy:
    runs-on: ubuntu-latest
    outputs:
      requires: ${{ steps.paths.outputs.requires }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: paths
        env:
          BASE: ${{ github.event.pull_request.base.sha }}
          HEAD: ${{ github.event.pull_request.head.sha }}
        run: |
          if git diff --quiet "$BASE" "$HEAD" -- src/ tools/; then
            echo "requires=false" >> "$GITHUB_OUTPUT"
          else
            echo "requires=true" >> "$GITHUB_OUTPUT"
          fi

  verified:
    needs: policy
    permissions:
      contents: read
      checks: write
      pull-requests: write
    uses: Oaklight/outboard/.github/workflows/verify.yml@<full commit SHA>
    with:
      pr: ${{ github.event.pull_request.number || 0 }}
      commit: ${{ github.event.pull_request.head.sha }}
      job: smoke
      required: ${{ needs.policy.outputs.requires == 'true' }}
```

The `uses:` reference is pinned to a commit SHA. A tag is mutable.

## 7. Keys

- Public keys live in `allowed_signers`, committed in the consumer repository and
  read from the default branch.
- One principal per operator group, for example `operator`. A principal may
  list several keys.
- Rotation: add the new key, start signing with it, remove the old key once no
  receipt that matters depends on it.
- Revocation: remove the line in a commit.
- The private key never enters the repository, a receipt, an artifact, or a log.
  It stays on the operator machine with mode `0600`.
- Outboard does not manage keys. There is no key server.

## 8. What a receipt proves

It proves that the holder of a listed private key signed these exact bytes, at
the claimed time, binding one repository, commit, tree, job, and evidence digest.

It does **not** prove:

- that the job actually ran, or ran correctly;
- that the evidence matches the digest (only that the signer claimed a digest;
  reproduction is a later, manual step);
- that the signing machine was not compromised;
- that the commit is what will merge (the tree is recorded for this reason);
- that `issued_at` is accurate — it is self-claimed.

A receipt is an attestation by a key holder. It is not a proof of correctness.

## 9. Versioning

- `schema` is the compatibility boundary. A v1 verifier accepts only
  `receipt/v1`.
- Adding, removing, or renaming a field, or changing any semantics, produces a
  new schema version. There is no tolerant parsing.
- `tool` is informational and never affects verification.
- v0.1 verifiers must keep accepting `receipt/v1` for the life of the 0.x and
  1.x lines.

## 10. Deferred to later versions

- A `publish` command (commit statuses only, unless an App identity exists).
- Gating on `tree` by default.
- Non-GitHub forges. The receipt format is forge-agnostic; only the workflow is
  GitHub-specific.
- Sigstore or keyless signing. It requires an OIDC identity and cannot sign on a
  machine outside Actions, which defeats the purpose.
