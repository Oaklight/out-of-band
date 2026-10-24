# Scenario: several jobs or machines

[English](scenario-multi-job.md) | [中文](../zh/scenario-multi-job.md)

One commit can be attested by several jobs: a smoke test on an old GPU, a
benchmark on a new one, a numerical check on a cluster. Each gets its own
receipt and its own check.

## One caller job per receipt

A job that calls a reusable workflow cannot carry a matrix, so declare one job
per name:

```yaml
jobs:
  v100:
    uses: Oaklight/outboard/.github/workflows/verify.yml@<full-sha>
    with:
      pr: ${{ github.event.pull_request.number }}
      commit: ${{ github.event.pull_request.head.sha }}
      job: v100-smoke
      check-name: v100-smoke-verified
      trusted-authors: your-login

  a100:
    uses: Oaklight/outboard/.github/workflows/verify.yml@<full-sha>
    with:
      pr: ${{ github.event.pull_request.number }}
      commit: ${{ github.event.pull_request.head.sha }}
      job: a100-bench
      check-name: a100-bench-verified
      required: false
      trusted-authors: your-login
```

Each call reads only the receipt whose `job` equals its own, so the two receipts
can live in separate comments on the same PR. This is why collection filters by
job: two valid receipts for one commit would otherwise look like a disagreement.

`required: false` is how optional platforms work. An absent receipt becomes
`not applicable` with a `success` conclusion, so a PR is not held hostage by
hardware that happened to be unavailable.

## Requiring "at least one"

Branch protection requires every named check; there is no OR. If the policy is
"any one of these platforms", add an aggregator:

```yaml
  any-platform:
    needs: [v100, a100]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - env:
          V100: ${{ needs.v100.outputs.verdict }}
          A100: ${{ needs.a100.outputs.verdict }}
        run: |
          if [ "$V100" = "verified" ] || [ "$A100" = "verified" ]; then
            exit 0
          fi
          echo "no platform verified: v100=$V100 a100=$A100"
          exit 1
```

Require `any-platform` in branch protection instead of the individual checks.
If every platform must pass, do the opposite: require each check and drop the
aggregator.

## Naming

- `job` lives inside the receipt. It is the operator's `--job`.
- `check-name` is the branch protection handle. It should say what was tested,
  not who ran it.
- Keep both stable. Changing either turns existing receipts or existing
  protection into no-ops.

## Evidence

Each call takes its own `evidence-url`. If one bundle covers several jobs,
either sign one receipt per job over the same directory, so every digest
matches, or split the directory. A bundle that does not match its signed digest
is `E_EVIDENCE_MISMATCH`.
