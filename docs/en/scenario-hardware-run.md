# Scenario: record a benchmark or model run

[English](scenario-hardware-run.md) | [中文](../zh/scenario-hardware-run.md)

A run happened on a machine GitHub cannot reach: a rented V100, a lab server, a
cluster. You want the result attached to a commit with enough detail to be
useful six months later.

## What "attached" means

A check run belongs to a commit. It is not attached to a branch, a release, or a
person. So the first decision is which commit you are attesting.

- A PR under review: the head commit. Wiring is the same as
  [Patch gate](scenario-patch-gate.md).
- A release or a tag: the commit the tag points to. There is no PR to comment
  on, so submit by dispatch.
- A long-lived branch: the pushed commit, submitted after the fact.
  [Branch gate](scenario-branch-gate.md) covers that case.

## Signing

```bash
# On the machine that ran the job. No network needed.
outboard sign \
  --job v100-bench \
  --commit 6e5b8a482f1baf41c8080b79501294cbf4057987 \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/outboard \
  --repo owner/repo \
  --output-file ./summary.txt \
  --out receipt.md
```

Keep the evidence directory small and meaningful: command lines, logs, the
numbers you will want later. `outboard pack` turns it into a deterministic
archive:

```bash
outboard pack --evidence-dir ./evidence --out evidence.tgz
```

The digest in the receipt covers the directory contents, so whatever you sign is
bound. Packing after signing is fine; the archive must contain exactly the same
files.

## Delivering the evidence

The verifier can fetch the bundle and keep it as an artifact. It needs an HTTPS
URL reachable from GitHub's runner:

```bash
gh workflow run bench-gate.yml \
  -f commit=6e5b8a482f1baf41c8080b79501294cbf4057987 \
  -F receipt=@receipt.md \
  -f evidence-url=https://example.com/evidence/6e5b8a4.tgz
```

`-F` reads the value from a file, which avoids the quoting problems a multi-line
block causes in a shell.

Common places to put the bundle: an `evidence/<sha>` branch in the same repo, a
release asset, or an object store with a signed URL. The transport does not need
to be trusted. The workflow recomputes the digest and refuses to publish if it
differs from what was signed.

Size limits: 50 MiB per bundle, 4 KiB of `output`. Curate. A full training log
belongs in an artifact store, not in the receipt.

## A dispatch-only gate

For a repository that does not gate PRs, one small caller is enough:

```yaml
name: bench gate

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
      job: v100-bench
      check-name: v100-bench-verified
      receipt: ${{ inputs.receipt }}
      evidence-url: ${{ inputs.evidence-url }}
```

`pr: "0"` means no comments are scanned and no sticky comment is posted. The
check is created on `inputs.commit`; the run itself can be dispatched from any
branch.

You can also dispatch a receipt for an older commit. The check appears on that
commit, not on the branch head. That is the point: it is a statement about the
code that was tested.

## Long jobs

The gate never waits. It runs when something triggers it — a PR update, a
comment, a dispatch — checks the receipts that exist at that moment, and exits
in seconds. A job that takes three hours or three days is the normal case: sign
when it finishes, then post or dispatch.

Real limits:

- The verify job itself times out after 5 minutes; fetching evidence gets 120
  seconds. Neither has anything to do with how long the job ran.
- If the PR head moves while the job runs, the receipt names the old head and
  is ignored as `E_WRONG_COMMIT`. Sign the new head.
- A receipt does not expire. Sign one per commit you care about, not per day.
  If policy needs "ran recently", enforce it outside the gate.
- A required check that has never run keeps a PR blocked. That is usually what
  you want while the hardware test is still in progress.

## Reading the result

- The check run shows the verdict, and in its output the claims and the folded
  `output` text.
- The run's step summary repeats the verdict, the source, and the evidence
  status.
- If a bundle was uploaded, it is on the run as `outboard-evidence`, subject to
  Actions retention (90 days by default).
- The PR comment, when there is one, is the durable record; the check is not.

## After a force-push

The commit is still reachable by SHA, and the check stays with it. A branch that
no longer contains that commit will not show it. If the same code is rewritten,
sign the new commit; a receipt never transfers.
