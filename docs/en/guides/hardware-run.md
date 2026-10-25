# Guide: record a benchmark or model run

[English](hardware-run.md) | [中文](../../zh/guides/hardware-run.md)

A run happened on a machine GitHub cannot reach: a rented V100, a lab server, a
cluster. You want the result attached to a commit with enough detail to be
useful six months later.

## What "attached" means

A check run belongs to a commit. It is not attached to a branch, a release, or
an identity. The first decision is which commit you are attesting.

- A pull request under review: the head commit. Wiring is the same as
  [Patch gate](patch-gate.md).
- A release or a tag: the commit the tag points to. There is no pull request to
  comment on, so submit by dispatch.
- A long-lived branch: the pushed commit, submitted after the fact.
  [Branch gate](branch-gate.md) covers that case.

## Sign

```bash
# On the machine that ran the job. No network needed.
oob sign \
  --job v100-bench \
  --commit 6e5b8a482f1baf41c8080b79501294cbf4057987 \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/out-of-band \
  --repo owner/repo \
  --output-file ./summary.txt \
  --out receipt.md
```

Keep the evidence directory small and meaningful: command lines, logs, the
numbers you will want later. `oob pack` turns it into a deterministic archive:

```bash
oob pack --evidence-dir ./evidence --out evidence.tgz
```

The digest in the receipt covers the directory contents, so whatever you sign is
bound. Packing after signing is fine; the archive must contain exactly the same
files.

`--output-file` is optional and caps at 4 KiB. It is the part a reviewer sees
folded under the check summary, so put the numbers there and leave the full log
for the archive.

## Deliver the evidence

Evidence is required by default. The verifier can fetch the bundle and keep it
as an artifact; it needs either an HTTPS URL reachable from the runner, or a
path on the runner (`evidence-file`).

```bash
gh workflow run bench-gate.yml \
  -f commit=6e5b8a482f1baf41c8080b79501294cbf4057987 \
  -F receipt=@receipt.md \
  -f evidence-url=https://example.com/evidence/6e5b8a4.tgz
```

`-F` reads the value from a file, which avoids the quoting problems a
multi-line block causes in a shell.

Common places to put the bundle: an `evidence/<sha>` branch in the same
repository, a release asset, or an object store with a signed URL. The transport
does not need to be trusted. The workflow recomputes the digest and refuses to
publish a pass if it differs from what was signed.

If the archive never leaves the runner, pass `evidence-file` instead of
`evidence-url`. If you want to skip the archive entirely, set
`require-evidence: false`; the receipt still carries the digest, and the
summary says `digest only`.

Size limits: 50 MiB per bundle, 4 KiB of `output`. Curate. A full training log
belongs in an artifact store, not in the receipt.

## A dispatch-only gate

For a repository that does not gate pull requests, one small caller is enough:

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
    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.5.0
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
commit, not on the branch head, because the receipt is a statement about the
code that was tested.

## Long jobs

The gate never waits. It runs when something triggers it (a pull request
update, a comment, a dispatch), checks the receipts that exist at that moment,
and exits in seconds. A job that takes three hours or three days is the normal
case: sign when it finishes, then post or dispatch.

Real limits:

- The reusable workflow's job times out after 5 minutes; fetching evidence gets
  120 seconds. Neither has anything to do with how long the job ran.
- If the pull request head moves while the job runs, the receipt names the old
  head and is ignored as `E_WRONG_COMMIT`. Sign the new head.
- A receipt does not expire. Sign one per commit you care about, not per day.
  If policy needs "ran recently", enforce it outside the gate.
- A required check that has never run keeps a pull request blocked. That is
  usually what you want while the hardware test is still in progress.

## Read the result

- The check run shows the verdict, and in its output the claims and the folded
  `output` text.
- The run's step summary repeats the verdict, the source, and the evidence
  status, and lists the evidence manifest with bounded text previews.
- If a bundle was supplied, it is on the run as `oob-evidence`, subject to
  Actions retention (90 days by default).
- The pull request comment, when there is one, is the durable record.

## After a force-push

The commit is still reachable by SHA, and the check stays with it. A branch that
no longer contains that commit will not show it. If the same code is rewritten,
sign the new commit; a receipt never transfers.
