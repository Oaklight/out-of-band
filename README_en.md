<h1 align="center">out-of-band</h1>

<p align="center">Out-of-band receipts for CI gates.</p>

<p align="center">
  <a href="https://pypi.org/project/out-of-band/"><img src="https://img.shields.io/pypi/v/out-of-band?color=green" alt="PyPI"></a>
  <a href="https://github.com/Oaklight/out-of-band/releases/latest"><img src="https://img.shields.io/github/v/release/Oaklight/out-of-band?color=green" alt="Release"></a>
  <a href="https://github.com/Oaklight/out-of-band/actions/workflows/ci.yml"><img src="https://github.com/Oaklight/out-of-band/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="Apache-2.0"></a>
</p>

<p align="center">
  <a href="README_en.md">English</a> | <a href="README_zh.md">中文</a>
</p>

<p align="center">
  <a href="https://oaklight.github.io/out-of-band/"><strong>Take the guided tour →</strong></a>
</p>

## Why this exists

Picture a pull request that only one machine can really test. The code needs a
particular accelerator, a licensed toolchain, a database reachable only from
the office network, or a lab box that several people share. GitHub's runners
cannot get there, and the check cannot move.

Putting a runner on that machine is usually worse than the problem:

- A **self-hosted runner** means a long-lived daemon on shared hardware, a
  GitHub credential that can pick up jobs, and repository code executing on the
  box.
- **Uploading logs and artifacts** leaves the merge decision to a person
  reading files in a browser tab.
- **Skipping the check** turns the gate into a suggestion.

Out-of-band takes a fourth route. The check runs where it already runs and produces
a small signed statement: this repository, this commit, this job, this result,
this evidence digest. That statement is the only thing that travels. A hosted
workflow verifies the signature over the exact bytes, checks the bindings, and
publishes the verdict as a check run. The operator machine needs no inbound
path and holds no GitHub credential.

The same mechanism covers a case with nothing exotic in it: you already ran the
test locally. Re-running it on a runner can take longer than the change took to
write, can fail for reasons the local run did not, or can return a slightly
different number. A signed receipt lets the gate accept the run you have.

If no valid statement arrives, the result is `unverified` and the merge stays
blocked. "Did not run" and "ran and failed" remain different states.

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
pip install out-of-band
```

Python 3.11+ and OpenSSH with `ssh-keygen -Y sign` (OpenSSH 8.0+). No runtime
dependencies.

## Quickstart

Generate a key on the operator machine. It never leaves the machine.

```bash
ssh-keygen -t ed25519 -N "" -C "ci operator" -f ~/.ssh/out-of-band
```

Commit the public key in the consumer repository as `.github/allowed_signers`:

```
operator ssh-ed25519 AAAA...
```

Sign a result for one commit. `--commit` must be a full SHA that exists in the
local clone; the tree is read from the commit, not the worktree.

```bash
oob sign \
  --job smoke \
  --commit "$(git rev-parse HEAD)" \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/out-of-band \
  --output-file ./check-output.txt
```

That prints one block: an HTML marker, one line of JSON, and an SSH signature.
Post it as a PR comment, or hand it to a `workflow_dispatch` input.

`--output-file` is optional. It embeds up to 4 KiB of what the check printed
into the signed receipt (schema `receipt/v2`), and the check page shows it
folded under the summary. Without it the receipt stays `receipt/v1`.

Verify locally before posting:

```bash
oob verify --block block.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/name --commit "$SHA" --expect-job smoke
```

## Documentation

Scenario guides live in [docs/](docs/en/README.md): a patch gate, a benchmark run,
branch attestation without a PR, several jobs on one commit, air-gapped hosts,
and operations. Start there rather than from the input list below.

## Wiring a consumer

```yaml
name: receipt gate

on:
  pull_request_target:
    types: [opened, synchronize, reopened, ready_for_review]
  issue_comment:
    types: [created]

permissions:
  contents: read
  checks: write
  pull-requests: write

jobs:
  policy:
    # A receipt arriving as a comment must trigger a fresh run.
    if: >
      github.event_name == 'pull_request_target' ||
      (github.event_name == 'issue_comment' &&
       github.event.issue.pull_request != null &&
       contains(github.event.comment.body, '<!-- receipt:v1 -->'))
    runs-on: ubuntu-latest
    outputs:
      pr: ${{ steps.context.outputs.pr }}
      commit: ${{ steps.context.outputs.commit }}
      requires: ${{ steps.paths.outputs.requires }}
    steps:
      - id: context
        env:
          GH_TOKEN: ${{ github.token }}
          PR_NUMBER: ${{ github.event.pull_request.number || github.event.issue.number }}
        run: |
          commit="$(gh api "repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER" --jq .head.sha)"
          echo "pr=$PR_NUMBER" >> "$GITHUB_OUTPUT"
          echo "commit=$commit" >> "$GITHUB_OUTPUT"

      - id: paths
        env:
          GH_TOKEN: ${{ github.token }}
          PR: ${{ steps.context.outputs.pr }}
        run: |
          if gh api --paginate "repos/$GITHUB_REPOSITORY/pulls/$PR/files?per_page=100" \
               --jq '.[].filename' | grep -qE '^src/'; then
            echo "requires=true" >> "$GITHUB_OUTPUT"
          else
            echo "requires=false" >> "$GITHUB_OUTPUT"
          fi

  verified:
    needs: policy
    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.4.0
    with:
      pr: ${{ needs.policy.outputs.pr }}
      commit: ${{ needs.policy.outputs.commit }}
      job: smoke
      required: ${{ needs.policy.outputs.requires == 'true' }}
      check-name: smoke-verified
      trusted-authors: operator-login
```

Then make `smoke-verified` a required check in branch protection. The check name
is public API: renaming it silently changes what the branch protects.

The example uses `pull_request_target`, not `pull_request`: it runs the default
branch's copy, so a PR cannot edit the gate that judges it. It gets a write
token, including for fork PRs, so never check out or run PR code here. The
verifier reads `allowed_signers` from the default branch and treats the receipt
as data. The `policy` job resolves the head through the API so a comment on an
issue does not fall back to `github.sha`, which is the base branch.

Inputs: `pr`, `commit`, `job`, `required`, `check-name`, `receipt`,
`allowed-signers`, `trusted-authors`, `evidence-url`. Output: `verdict`.

Pin `uses:` by full commit SHA and keep the version in a comment
(`# v0.4.0`); Dependabot can open the bump PR. A tag can be moved.

### Uploading evidence

Empty `evidence-url` keeps the current behaviour: the receipt commits to a
digest and nothing is uploaded.

Set it to an HTTPS URL of a bundle made with `oob pack`, and the workflow
downloads it, extracts it safely, recomputes the digest, and uploads it as the
`oob-evidence` artifact. A mismatch makes the check unverified.

```bash
oob pack --evidence-dir ./evidence --out evidence.tgz
```

### Receipt collection

- `receipt` input, when set, wins. Use it for `workflow_dispatch`.
- Otherwise the workflow reads issue comments on `pr` and keeps only comments
  from trusted authors: `trusted-authors` if set, else `OWNER`, `MEMBER`, or
  `COLLABORATOR`. Untrusted markers are ignored, so a stranger cannot stall the
  gate by posting one.
- Blocks naming an older commit are ignored, so a re-run can post a fresh
  receipt without deleting the previous one. Only an expected-commit block is
  a candidate at all.
- Byte-identical blocks are accepted as one; blocks for the expected commit
  that disagree are `E_MULTI_BLOCK`.

### Triggers and forks

`pull_request` from a fork gets a read-only token, so nothing can be published.
Use `pull_request_target` (default-branch code, no PR checkout) or
`issue_comment` for forks. `pull_request` also runs the PR's own copy of the
workflow, which lets a contributor weaken the gate; avoid it for this job.

### Credentials

`sign` and `verify` need no GitHub credential and work with the network off.
Publishing needs a GitHub App identity; inside Actions the automatic
`GITHUB_TOKEN` is the Actions App. A PAT can create only commit statuses, so
there is no CLI publish command.

### Air-gapped operator hosts

The signing host can have no outbound network at all. Run the single-file
`oob.pyz` (or install the wheel) from the release, carry the repository as a `git bundle`, and carry the
receipt and evidence out by hand. See [docs/offline.md](docs/en/offline.md).

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

## The name

Out-of-band means the check runs outside the normal CI path. GitHub still
receives the result, but the job and the signature happen somewhere else: a lab
machine, an HPC login node, a rented GPU. What crosses back is a signed receipt.

The command is `oob`, the short form. The package and the repository use the
full name, `out-of-band`.

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

`SPEC.md` is normative. `docs/en/validation.md` records the operator-host test.
The self-test workflow signs four receipts and asserts that valid ones pass and
forged ones do not.

## Non-goals

No runner, no hosted service, no GitHub App, no Sigstore, no artifact storage.
