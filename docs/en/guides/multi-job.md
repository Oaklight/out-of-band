# Guide: several jobs or machines

[English](multi-job.md) | [中文](../../zh/guides/multi-job.md)

One commit can be attested by several jobs: a smoke test on an old GPU, a
benchmark on a new one, a numerical check on a cluster. Each gets its own
receipt and its own check.

## One caller per receipt

With the reusable workflow, a job that calls it cannot carry a matrix, so
declare one job per name:

```yaml
jobs:
  v100:
    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.5.0
    with:
      pr: ${{ github.event.pull_request.number }}
      commit: ${{ github.event.pull_request.head.sha }}
      job: v100-smoke
      check-name: v100-smoke-verified
      trusted-authors: your-login

  a100:
    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.5.0
    with:
      pr: ${{ github.event.pull_request.number }}
      commit: ${{ github.event.pull_request.head.sha }}
      job: a100-bench
      check-name: a100-bench-verified
      required: false
      trusted-authors: your-login
```

The snippet omits the evidence source. Add `evidence-url` or `evidence-file` to
each call, or set `require-evidence: false`.

With the [action](../reference/action.md), the same shape fits in one job with a
matrix:

```yaml
jobs:
  verify:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - job: v100-smoke
            check: v100-smoke-verified
          - job: a100-bench
            check: a100-bench-verified
    steps:
      - uses: Oaklight/out-of-band@<full-sha> # v0.5.0
        with:
          commit: ${{ github.event.pull_request.head.sha }}
          job: ${{ matrix.job }}
          check-name: ${{ matrix.check }}
```

Both shapes produce one check per job name. The action version saves the
per-job boilerplate; the workflow version gives each receipt its own job
boundary. [multi-job.yml](../../../examples/multi-job.yml) is the action shape,
complete.

Each call reads only the receipt whose `job` equals its own, so the receipts
can live in separate comments on the same pull request. This is why collection
filters by job: two valid receipts for one commit would otherwise look like a
disagreement.

`required: false` is how optional platforms work. An absent receipt becomes
`not applicable` with a `success` conclusion, so a pull request is not held
hostage by hardware that happened to be unavailable.

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

Each call needs its own evidence source unless you set
`require-evidence: false`. If one bundle covers several jobs, sign one receipt
per job over the same directory, so every digest matches, and point each call
at the same archive. Or split the directory per job.

A bundle that does not match its signed digest is `E_EVIDENCE_MISMATCH`. See
[Evidence](../concepts/evidence.md) for the three sources and the limits.
