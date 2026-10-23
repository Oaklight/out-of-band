# outboard

Out-of-band receipts for CI gates.

A job runs where GitHub cannot reach it, signs a receipt bound to a commit, and
a hosted workflow verifies that receipt and publishes the verdict as a check.
The machine that signs needs no inbound path and no GitHub credential.

```
operator host                          GitHub
─────────────                          ──────
check ──► evidence ──► sign            PR comment / dispatch
                          │                    │
                          └── signed block ────┴──► verify.yml
                                                      │
                                                      ├── check run
                                                      ├── step summary
                                                      └── sticky comment
```

The split is deliberate: this repository owns the mechanism (format, signing,
verification, publishing). The consumer owns the policy (which paths need a
receipt, the job name, which key, required or optional).

## Three states, never collapsed

| Receipt | Exit | Check conclusion |
|---|---|---|
| valid, `result: pass` | 0 | `success` |
| valid, `result: fail` | 1 | `failure` |
| absent or invalid | 2 | `action_required` |
| usage or internal error | 3 | nothing published; the job fails |

A missing receipt is **unverified**, never skipped. If the tool cannot run, the
required check stays pending and the merge stays blocked.

## Install

```bash
pip install outboard
```

Python 3.11+ and OpenSSH with `ssh-keygen -Y sign` (OpenSSH 8.0+). No runtime
dependencies.

## Quickstart

Generate a key on the operator machine. It never leaves the machine.

```bash
ssh-keygen -t ed25519 -N "" -C "ci operator" -f ~/.ssh/outboard
```

Commit the public key in the consumer repository as `.github/allowed_signers`:

```
operator ssh-ed25519 AAAA...
```

Sign a result for one commit. `--commit` must be a full SHA that exists in the
local clone; the tree is read from the commit, not the worktree.

```bash
outboard sign \
  --job smoke \
  --commit "$(git rev-parse HEAD)" \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/outboard
```

That prints one block: an HTML marker, one line of JSON, and an SSH signature.
Post it as a PR comment, or hand it to a `workflow_dispatch` input.

Verify locally before posting:

```bash
outboard verify --block block.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/name --commit "$SHA" --expect-job smoke
```

## Wiring a consumer

```yaml
name: receipt gate

on:
  pull_request:
  issue_comment:
    types: [created]

permissions:
  contents: read
  checks: write
  pull-requests: write

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
          if git diff --quiet "$BASE" "$HEAD" -- src/; then
            echo "requires=false" >> "$GITHUB_OUTPUT"
          else
            echo "requires=true" >> "$GITHUB_OUTPUT"
          fi

  verified:
    needs: policy
    uses: Oaklight/outboard/.github/workflows/verify.yml@<full commit SHA>
    with:
      pr: ${{ github.event.pull_request.number || 0 }}
      commit: ${{ github.event.pull_request.head.sha || github.sha }}
      job: smoke
      required: ${{ needs.policy.outputs.requires == 'true' }}
      check-name: smoke-verified
      trusted-authors: operator-login
```

Then make `smoke-verified` a required check in branch protection. The check name
is public API: renaming it silently changes what the branch protects.

Inputs: `pr`, `commit`, `job`, `required`, `check-name`, `receipt`,
`allowed-signers`, `trusted-authors`. Output: `verdict`.

Pin `uses:` by commit SHA. A tag is mutable.

### Receipt collection

- `receipt` input, when set, wins. Use it for `workflow_dispatch`.
- Otherwise the workflow reads issue comments on `pr` and keeps only comments
  from trusted authors: `trusted-authors` if set, else `OWNER`, `MEMBER`, or
  `COLLABORATOR`. Untrusted markers are ignored, so a stranger cannot stall the
  gate by posting one.
- Byte-identical blocks are accepted as one; blocks that disagree are
  `E_MULTI_BLOCK`.

### Triggers and forks

`pull_request` from a fork gets a read-only token, so nothing can be published.
Use `pull_request_target` (default-branch code, no PR checkout) or
`issue_comment` for forks.

### Credentials

`sign` and `verify` need no GitHub credential and work with the network off.
Publishing needs a GitHub App identity; inside Actions the automatic
`GITHUB_TOKEN` is the Actions App. A PAT can create only commit statuses, so
there is no CLI publish command.

### Retention

Checks and workflow runs follow the Actions retention setting (90 days by
default; 90 is the maximum for public repositories). The receipt in the PR
comment is the durable record, and the evidence directory stays on the operator
side.

## What a receipt proves

That the holder of a listed key signed these exact bytes, binding one
repository, commit, tree, job, and evidence digest.

It does not prove that the job ran correctly, that the evidence matches the
digest, or that the host was uncompromised. It is an attestation, not a proof
of correctness. See [SPEC.md](SPEC.md) §8.

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

`SPEC.md` is normative. `docs/validation.md` records the operator-host test.
The self-test workflow signs four receipts and asserts that valid ones pass and
forged ones do not.

## Non-goals

No runner, no hosted service, no GitHub App, no Sigstore, no artifact storage.
