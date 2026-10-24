# Scenario: attest pushes, without a PR

[English](scenario-branch-gate.md) | [中文](scenario-branch-gate.zh.md)

Some repositories deploy straight from a branch, or hold artifacts that no pull
request touches: models, firmware images, datasets. You still want a signed
statement about the exact commit.

## The honest limitation

Required status checks are enforced when a pull request merges. On a direct
push, GitHub cannot require a check that only runs after the push lands. A
branch gate is therefore one of three things:

- **advisory**: publish the check and let people see it;
- **retroactive**: the push lands, the operator dispatches a verification, and
  the check turns green on that commit;
- **preventive**: require pull requests, even self-approved ones, and use the
  [patch gate](scenario-patch-gate.md).

Pick deliberately. Calling an advisory check "enforced" is worse than not having
one.

## Wiring it

```yaml
name: attestation

on:
  workflow_dispatch:
    inputs:
      commit:
        required: true
      receipt:
        required: true
      evidence-url:
        default: ""

permissions:
  contents: read
  checks: write
  pull-requests: write

jobs:
  verified:
    uses: Oaklight/outboard/.github/workflows/verify.yml@<full-sha>
    with:
      pr: "0"
      commit: ${{ inputs.commit }}
      job: release-smoke
      check-name: release-smoke-verified
      receipt: ${{ inputs.receipt }}
      evidence-url: ${{ inputs.evidence-url }}
```

To let a push trigger the same call, add `push: branches: [main]` and pass
`commit: ${{ github.sha }}`. That run will be unverified at first, because no
receipt exists yet; the dispatch supplies one afterwards.

## Supplying the receipt

The `receipt` input takes the block as text. Let `gh` read it from a file:

```bash
gh workflow run attestation.yml \
  -f commit="$(git rev-parse origin/main)" \
  -F receipt=@receipt.md
```

If the block has been through a shell already and the backticks look suspicious,
go straight to the API, which takes JSON:

```bash
jq -n --rawfile r receipt.md --arg c "$(git rev-parse origin/main)" \
  '{ref: "main", inputs: {commit: $c, receipt: $r}}' \
| gh api repos/OWNER/REPO/actions/workflows/attestation.yml/dispatches --input -
```

## Committing the receipt to the repository

A block committed to a branch can be read by the caller and passed as `receipt`.
It cannot live in the commit under test, because the workflow checks out the
default branch. This suits a dedicated "attestations" branch that records what
was verified and when; it is not a substitute for signature verification, which
still runs. Keep it out of the main path unless you need the paper trail.

## Verification is the same

Whatever the transport, the verifier checks the signature against the default
branch's `allowed_signers` and binds repository, commit, tree, and job. A
receipt for a different commit is `E_WRONG_COMMIT`.
