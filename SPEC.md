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
- Value: string (≤ 256 bytes, no control characters), integer with
  `|n| ≤ 9007199254740991` (2^53−1, so every JSON consumer can hold it
  exactly), boolean, or an array of at most 16 of those scalars. No nested
  objects, no arrays of arrays, no floats, no null.
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
2. The first line after the marker whose trimmed content is exactly
   ```` ```json ```` opens the JSON block. Any other content on that line is
   invalid.
3. The payload is every line up to the next line whose trimmed content is
   exactly ```` ``` ````. The payload must contain no line break; two or more
   lines → `E_MULTI_LINE`. A missing closing fence → `E_BAD_FENCE`.
4. Skip whitespace-only lines. The next such line must be exactly
   ```` ```ssh-signature ````. A missing fence or an unterminated signature is
   `E_BAD_FENCE`.
5. If any step fails, the block is invalid.

Byte grammar:

- A line break is LF (`\n`) only. A CR is payload data, not a line terminator,
  so a CRLF comment fails signature verification instead of being normalized.
- "Trimmed" means leading and trailing spaces and tabs removed. The payload
  itself is never trimmed.
- The signed payload is the exact bytes between the two newlines that bound the
  single JSON line. No normalization of any kind.

Trailing content after the signature fence is ignored.

When the receipt is collected from PR comments (workflow mode, §6.4), only
comments from trusted authors count. If no trusted comment carries a marker,
the receipt is absent. Among trusted comments: byte-identical blocks are
accepted as one; any two that differ make the receipt invalid. A marker-bearing
trusted comment with a malformed envelope is invalid, not absent. Markers in
untrusted comments are ignored entirely, so anyone can post one without
affecting the verdict.

## 2. Evidence digest

The evidence directory is never uploaded. The receipt commits to it so the
operator can reproduce it later.

### 2.1 Algorithm

1. Walk the directory recursively. Include every regular file, including
   dotfiles and files in subdirectories.
2. Reject the whole operation on any symlink, FIFO, socket, or device file.
   Do not follow symlinks.
3. For each file, compute `sha256` over its raw bytes.
4. Paths are relative to the evidence directory, use `/` as the separator,
   never contain `.` or `..` components, must be valid UTF-8, and must not
   contain LF, CR, or NUL. A path that violates this is a hard error
   (`E_EVIDENCE_PATH`). It is never skipped: skipping would let two different
   trees produce identical manifest bytes.
5. Build one manifest line per file:

   ```text
   <64 lowercase hex><SPACE><SPACE><relative path><LF>
   ```

6. Sort lines by the unsigned byte order of the UTF-8 encoded path.
7. `digest = "sha256:" + hex(sha256(manifest bytes))`.
8. `count` is the number of files.

An empty directory is valid: `count` is 0 and the digest is the SHA-256 of the
empty byte string,
`sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

File modes, ownership, and timestamps are not part of the digest.

### 2.2 Signer-side rules

- The private key must not live inside the evidence directory. Resolve both
  paths with `realpath` and refuse with `E_KEY_IN_EVIDENCE` **before** walking
  the directory, so the key's name and hash never enter the digest.
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
6. **Bindings.** In this order: `repo` (case-insensitive), `commit`
   (case-insensitive), `tree` (only when the caller passes `--expect-tree`),
   then `job` (exact) → `E_WRONG_REPO`, `E_WRONG_COMMIT`, `E_WRONG_TREE`,
   `E_WRONG_JOB`. Expected values come from the caller's context (the workflow
   inputs and the GitHub event), never from the receipt.
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
- Before calling `ssh-keygen`, check the armor: a `BEGIN SSH SIGNATURE` line, an
  `END SSH SIGNATURE` line, and a decodable base64 body. A malformed armor is
  `E_BAD_SIGNATURE`.
- After that, `ssh-keygen`'s exit status is the only signal. Nonzero for every
  principal means `E_NO_PRINCIPAL`. The text it prints about the matching key
  is not parsed.

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

| Code | Meaning | Exit |
|---|---|---|
| `OK` | verification succeeded (`pass` or valid `fail`) | 0 or 1 |
| `E_NO_BLOCK` | no receipt marker found | 2 |
| `E_MULTI_BLOCK` | more than one marker, or trusted comments that disagree | 2 |
| `E_TOO_LARGE` | block exceeds 16 KiB | 2 |
| `E_BAD_FENCE` | fences missing or in the wrong order | 2 |
| `E_MULTI_LINE` | JSON payload is not one line | 2 |
| `E_BAD_JSON` | not valid UTF-8 or not JSON | 2 |
| `E_DUP_KEY` | duplicate JSON object key | 2 |
| `E_UNKNOWN_FIELD` | field not defined by this schema | 2 |
| `E_BAD_SCHEMA` | `schema` is not `receipt/v1` | 2 |
| `E_BAD_TYPE` | wrong JSON type, float, or null | 2 |
| `E_BAD_VALUE` | value violates its pattern or range | 2 |
| `E_CLAIMS_LIMIT` | claims exceed count, size, or shape limits | 2 |
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

Every `sign` failure exits 3: no receipt was produced. Codes with exit 2 mean a
receipt was found and rejected, except `E_NO_BLOCK`, which means none was found.

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
- `--claims k=v` may repeat. Keys must match the claims key pattern; a repeated
  key is `E_USAGE`.
- `v` is parsed as JSON only when it is a valid JSON scalar or array literal of
  the shapes allowed by §1.2.1; otherwise it is a string. `null` and floats are
  `E_USAGE`. Integers outside `±9007199254740991` are `E_USAGE`.
- Arrays are accepted only as a JSON array literal of allowed scalars.
- The assembled object must satisfy §1.2.1, or the signer exits 3 with
  `E_CLAIMS_LIMIT`.
- Refuses a dirty worktree with `E_DIRTY_WORKTREE` unless `--allow-dirty`. Even
  then, the receipt binds a commit, so a dirty tree only helps for local
  experiment.
- Writes the block to stdout, or to `--out`.
- No network access, no GitHub credential, no machine identity.

### 5.2 `verify`

- `--block` accepts a file containing the marker and both fences. A bare JSON
  line with a separate signature is not accepted.
- Prints a human summary to stdout. With `--json`, prints exactly one line and
  nothing else:

  ```json
  {"verdict":"pass|fail|unverified|error","code":"OK|E_...","repo":null,"commit":null,"job":null}
  ```

  - `verdict` is `pass` or `fail` only when the receipt is valid; `code` is
    `OK`.
  - `verdict` is `unverified` for exit 2; `code` is the rejection code.
  - `verdict` is `error` for exit 3; `code` is the failure code.
  - `repo`, `commit`, and `job` are `null` unless the receipt parsed **and** its
    signature verified. Before that they are attacker-controlled and must not
    be presented as facts.
  - The line is printed for every handled outcome, including exit 3.
  - The exit code remains authoritative.
- Never executes anything from the receipt. The JSON payload is never passed to
  a shell, `eval`, or a template engine.

### 5.3 Not in v0.1

There is no `publish` command. Creating a check run requires a GitHub App
identity; inside Actions, `GITHUB_TOKEN` is the Actions App, so publishing lives
in the workflow (§6). A PAT can create only commit statuses, which is a different
object and is not this gate.

This is a deliberate deviation from the handoff, which listed `publish` as an
optional verb. Verified 2026-10-23: the check-runs API rejects a user token with
`You must authenticate via a GitHub App.`

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
| `trusted-authors` | string | `""` | comma-separated logins allowed to supply a receipt. Empty means comments whose `author_association` is `OWNER`, `MEMBER`, or `COLLABORATOR` |

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

1. Check out the caller repository at its **default branch** by setting
   `ref: ${{ github.event.repository.default_branch }}` explicitly, with
   `persist-credentials: false`. A bare `actions/checkout` on a
   `pull_request` event checks out the PR merge ref, which would let a PR
   supply its own `allowed_signers`. The file is never read from a PR
   checkout.
2. Install `outboard` at an exact version pinned in the workflow file. Inside
   the tool repository itself the workflow installs from the checked-out source
   instead, so the self-test exercises unreleased code; consumers always get
   the pinned release.
3. The only repository file read besides the workflow itself is
   `allowed-signers`.
4. Treat the receipt as data. Cap its size before parsing. Never interpolate it
   into a shell command.
5. Set a job timeout of 5 minutes.
6. On `pull_request` from a fork, `GITHUB_TOKEN` is read-only, so no check can
   be published. Fork PRs must be driven by `pull_request_target`,
   `issue_comment`, or `workflow_dispatch` (§6.9).

### 6.4 Receipt resolution

- If `receipt` is non-empty, use it.
- Else if `pr` > 0, page through the PR's issue comments and keep only comments
  from trusted authors:
  - when `trusted-authors` is non-empty, the author's login must be in that
    list (case-insensitive);
  - otherwise the comment's `author_association` must be `OWNER`, `MEMBER`, or
    `COLLABORATOR`.

  Untrusted comments are ignored whether or not they carry a marker, so anyone
  can post one without changing the verdict.
- Among trusted markers, only blocks whose `commit` equals the input `commit`
  are candidates. The field is read from the payload without trusting it, so a
  forged claim can hide a block from the candidate set but never authenticate
  one. A receipt for an earlier head is not evidence about this one: ignoring
  it lets an operator post a fresh receipt without deleting the previous one.
- If trusted markers exist but none names the expected commit, the receipt is
  absent with `E_WRONG_COMMIT`. If none of them can be parsed at all, the
  receipt is invalid with the parse error instead.
- Blocks for the expected commit that disagree with each other are
  `E_MULTI_BLOCK`. Byte-identical blocks count as one.
- Review comments and review bodies are not scanned. Only issue comments.
- Scanning stops at 5000 comments. Beyond that, exit 3 with
  `E_TOO_MANY_COMMENTS` instead of guessing.
- If no trusted comment carries a marker, the receipt is absent.

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
- The title and summary are built from fixed templates. `job`, the error code,
  and every claim value are rendered inside a fenced code block, with `@`, `[`,
  `]`, `<`, `>`, and backticks escaped. A claim can never become a link or a
  mention.
- A new check run is created per verification. The newest one wins for branch
  protection; older ones remain visible in the Checks tab.
- The check name is public API. Changing it silently changes what branch
  protection enforces.

### 6.7 Sticky comment

- One comment per PR, found by the marker `<!-- outboard:state -->` **and** an
  author matching `github-actions[bot]` (the Actions app; an installation token
  cannot call `GET /user`), edited in place with
  `PATCH /repos/{owner}/{repo}/issues/comments/{id}`.
- A foreign comment that carries the marker is ignored. It never causes a
  second sticky comment and is never edited.
- Create only when no such comment exists. Never delete or edit another actor's
  comments.
- The body is a fixed template plus one fenced code block for the dynamic
  values, escaped as in §6.6, so a claim cannot mention or link.
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

### 6.9 Triggers

The reusable workflow declares `workflow_call` only; the caller picks the
trigger.

- `workflow_dispatch` — the receipt is supplied through the `receipt` input.
- `issue_comment` — a trusted operator posts the receipt; the run executes
  default-branch code with a write token.
- `pull_request` — same-repository branches only. A fork PR gets a read-only
  `GITHUB_TOKEN`, so nothing can be published; use `pull_request_target`
  (default-branch code, no PR checkout) or `issue_comment` instead.

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
