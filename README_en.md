<h1 align="center">out-of-band</h1>

<p align="center">Signed receipts for CI checks that GitHub cannot run, or that already ran somewhere else.</p>

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

## Two reasons to sign a receipt

**GitHub cannot run the job.** The code needs a particular accelerator, a
licensed toolchain, a database reachable only from the office network, or a lab
box several people share. A hosted runner cannot get there.

**The job already ran somewhere else.** Re-running it in CI is slow, flaky, or
returns a different number. You want the gate to accept the run you have.

Both cases leave the same gap: a required check that no workflow can produce
honestly. Out-of-band closes it with a statement the machine can sign without a
GitHub credential and without an inbound path.

Putting a self-hosted runner on the machine is the usual alternative. It means a
long-lived daemon on shared hardware, a credential that can pick up jobs, and
repository code executing on the box. Uploading logs leaves the decision to
someone reading a browser tab. Skipping the check turns the gate into a
suggestion.

## How it works

```
operator host                          GitHub
─────────────                          ──────
run ──► evidence ──► sign              PR comment / dispatch
                        │                    │
                        └── signed block ────┴──► verify.yml
                                                    │
                                                    ├── check run
                                                    ├── step summary
                                                    └── sticky comment
```

1. The operator runs the job where it has to run and signs one statement: this
   repository, this commit, this tree, this job, this result, this evidence
   digest.
2. The statement travels as a pull request comment, a dispatch input, or a
   file.
3. A workflow on GitHub verifies the signature against
   `.github/allowed_signers` on the default branch, checks the bindings, and
   publishes a check run.

The repository owns the mechanism: format, signing, verification, publishing.
The consumer owns the policy: which paths need a receipt, the job name, which
key, and whether the check is required.

## Four states, never collapsed

| Receipt | Verifier state | Check conclusion |
| --- | --- | --- |
| valid, `result: pass` | `verified` | `success` |
| valid, `result: fail` | `failed` | `failure` |
| absent or invalid | `unverified` | `failure` |
| not required by policy | `not applicable` | `success` |

`unverified` means the gate could not tell. It publishes a `failure`, so a
required check stays closed, and the summary carries the error code. A missing
receipt is never a skip.

## Quickstart

Requires Python 3.10+ and OpenSSH 8.0+ (`ssh-keygen -Y sign`). No runtime
dependencies.

```bash
pip install out-of-band
```

Generate a key on the machine that runs the job. It never leaves that machine.

```bash
ssh-keygen -t ed25519 -N "" -C "ci operator" -f ~/.ssh/out-of-band
```

Commit the public key in the consumer repository as `.github/allowed_signers`:

```text
operator ssh-ed25519 AAAA...
```

Sign one commit. `--commit` must be a full SHA that exists in the local clone;
the tree is read from the commit, not the worktree.

```bash
oob sign \
  --job smoke \
  --commit "$(git rev-parse HEAD)" \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/out-of-band \
  --repo owner/name \
  --out receipt.md
```

That writes one block: an HTML marker, one line of JSON, and an SSH signature.
Post it as a pull request comment, or pass it to a `workflow_dispatch` input.
For a readable comment, run `oob render --block receipt.md` first.

Verify locally before posting:

```bash
oob verify --block receipt.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/name --commit "$(git rev-parse HEAD)" --expect-job smoke
```

Exit codes: `0` valid pass, `1` valid fail, `2` absent or invalid, `3` tool
error.

## Use it in a repository

Two carriers, one verifier. The [action](docs/en/reference/action.md) runs as a
step; the [reusable workflow](docs/en/reference/workflow.md) runs as its own job.

```yaml
  verified:
    needs: policy
    runs-on: ubuntu-latest
    permissions:
      contents: read
      checks: write
      pull-requests: write
    steps:
      - uses: Oaklight/out-of-band@<full-sha> # v0.5.0
        with:
          pr: ${{ needs.policy.outputs.pr }}
          commit: ${{ needs.policy.outputs.commit }}
          job: smoke
          required: ${{ needs.policy.outputs.requires }}
          check-name: smoke-verified
          trusted-authors: operator-login
```

The snippet shows the gate wiring. Evidence is required by default, so add
`evidence-url` or `evidence-file`, or set `require-evidence: false`.

Then require `smoke-verified` in branch protection. The check name is public
API: renaming it silently changes what the branch protects.

Pin `uses:` by full commit SHA. A tag can move.

## Evidence

Evidence is required by default. Supply the archive in one of three ways:

| Source | Use when |
| --- | --- |
| `evidence-file` | the archive is already on the runner |
| `evidence-url` | the archive is at an HTTPS address |
| `claims.evidence_url` | the receipt should carry its own location |

```bash
oob pack --evidence-dir ./evidence --out evidence.tgz
```

The verifier extracts the archive, recomputes the digest, and compares it with
the value that was signed. A mismatch is `E_EVIDENCE_MISMATCH` and the verdict
is `unverified`. A matching archive is uploaded as the `oob-evidence` artifact,
and the job summary shows a manifest plus bounded text previews.

Set `require-evidence: false` to accept the signed digest without an archive.

The GitHub token is sent only to `api.github.com` and `github.com`. Other hosts
must serve a public or signed URL.

## What a receipt proves

That the holder of a listed key signed these exact bytes, binding one
repository, commit, tree, job, and evidence digest.

It does not prove that the job ran correctly, that the evidence matches the
digest, or that the host was uncompromised. It is an attestation, not a proof
of correctness. See [Trust](docs/en/concepts/trust.md) and
[SPEC.md](SPEC.md) §8.

## Documentation

Start with the [docs map](docs/en/README.md). The short version:

| If you want to | Read |
| --- | --- |
| Install and sign the first receipt | [Get started](docs/en/start.md) |
| Understand receipts, trust, evidence, states | [Concepts](docs/en/README.md#read-by-what-you-are-doing) |
| Look up a command or an input | [CLI](docs/en/reference/cli.md), [action](docs/en/reference/action.md), [workflow](docs/en/reference/workflow.md) |
| Follow an end-to-end setup | [Patch gate](docs/en/guides/patch-gate.md), [hardware run](docs/en/guides/hardware-run.md) |
| Run it on an air-gapped host | [Air-gapped hosts](docs/en/guides/air-gapped.md) |
| Compare with other tools | [Prior art](docs/en/prior-art.md) |

Chinese documentation mirrors the English tree under [`docs/zh/`](docs/zh/README.md).

## Install

```bash
pip install out-of-band
```

Each release also carries `oob-<version>.pyz`, a single-file build that needs
only Python. It is the usual choice for a host that cannot reach PyPI.

Python 3.10 through 3.14 are tested. Windows works with `python oob-<version>.pyz`.

## Project

- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Examples](examples/README.md)
- [Normative specification](SPEC.md)
- License: Apache-2.0

## Non-goals

No runner, no hosted service, no GitHub App, no Sigstore, no transparency log,
no artifact storage. The tool signs and verifies a statement; everything else
belongs to the repository that uses it.
