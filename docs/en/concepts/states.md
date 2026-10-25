# States

[English](states.md) | [中文](../../zh/concepts/states.md)

The gate reports four states. They are never collapsed into two.

| State | Meaning | Check | Who acts |
| --- | --- | --- | --- |
| `verified` | a valid signature over `result: pass` | `success` | the merge can proceed |
| `failed` | a valid signature over `result: fail` | `failure` | fix the job and sign again |
| `unverified` | no usable receipt, a bad signature, or evidence that does not match | `failure` | a human looks |
| `not applicable` | no receipt was required for this change | `success` | nobody |

`unverified` is not a softer `failed`. It means the gate could not tell. A
required check stays red, and the summary carries the error code so the reason
is visible.

## Why `unverified` is a failure

A check has two conclusions that block a merge: `failure` and `neutral` (or a
missing check). Publishing `unverified` as `success` would let "I could not
tell" merge code. Publishing it as `failure` keeps the gate closed and still
distinguishes the reason in the title and summary.

The alternative, leaving the check pending, looks cleaner in the UI but is
worse in practice: a pending check can wait forever, and some policies treat a
stale pending check as a reason to merge anyway. The gate decides, then reports.

## How the states map to exit codes

| Receipt | `oob verify` exit | Verifier state | Check conclusion |
| --- | --- | --- | --- |
| valid, `result: pass` | 0 | `verified` | `success` |
| valid, `result: fail` | 1 | `failed` | `failure` |
| absent or invalid | 2 | `unverified` | `failure` |
| tool could not run | 3 | no check published | the job fails |

Exit 3 is not a verdict. It means the verifier itself could not do its job: a
missing file, a bad flag, a bug. No check is created, so a required check stays
missing and the merge stays blocked. That is the fail-closed result.

## `not applicable`

When the consumer sets `required: false`, the receipt is not evaluated at all.
The state is `not applicable`, the conclusion is `success`, and the summary says
the receipt was not evaluated. This is how path filters and optional platforms
work: a docs-only pull request should not need a hardware receipt.

A stale failing receipt must not block a pull request that the policy already
classified as not needing one, so the receipt is skipped, not read and
ignored after a failure.

## Reporting without publishing

`report: false` computes the verdict and writes the step summary and outputs,
but creates no check run and no sticky comment. The repository's self-test uses
this for negative cases: the verdict is asserted, and the pull request's check
list stays green.

This is a testing and dry-run tool, not a policy option. A consumer that needs
the gate must leave `report` at `true`.

## Error codes

`unverified` always arrives with a code such as `E_NO_BLOCK`, `E_WRONG_COMMIT`,
`E_BAD_SIGNATURE`, or `E_EVIDENCE_MISMATCH`. The code names the first check
that failed. The full list is in [CLI](../reference/cli.md#error-codes).
