# Action

[English](action.md) | [中文](../../zh/reference/action.md)

The action runs the verifier as a step inside a job you already have. The
[reusable workflow](workflow.md) runs it as its own job. Both publish the same
check run and read the same trust root.

Use the action when you want to keep the trigger, permissions, timeout, and
concurrency in your own workflow, or when you want verification in a job that
already does something else. Use the reusable workflow when you want a separate
job boundary and a verifier you do not configure.

| | Action | Reusable workflow |
| --- | --- | --- |
| Called from | a step, `uses: Oaklight/out-of-band@<sha>` | a job, `uses: Oaklight/out-of-band/.github/workflows/verify.yml@<sha>` |
| Runner | the caller's job | its own `ubuntu-latest` job |
| Permissions | the caller sets them | the workflow declares its own |
| Timeout, concurrency | the caller sets them | built in |
| Marketplace | eligible | not eligible |

## What the caller supplies

The action cannot declare any of these:

- the trigger, usually `pull_request_target` plus `issue_comment`;
- `permissions: contents: read, checks: write, pull-requests: write`;
- `check-name`, because branch protection matches that string;
- the commit and job name the receipt must carry.

The token defaults to `${{ github.token }}`. It must be allowed to create check
runs and edit pull request comments.

## Inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `commit` | required | commit SHA the receipt must name |
| `job` | required | job name the receipt must carry |
| `pr` | `0` | pull request for comment collection and the sticky comment; `0` disables both |
| `required` | `true` | whether this commit needs a receipt at all; the string `true` or `false` |
| `check-name` | `oob` | check run name |
| `receipt` | empty | receipt text; takes precedence over comments |
| `allowed-signers` | `.github/allowed_signers` | path in the caller repository, read from the default branch |
| `trusted-authors` | empty | comma-separated logins allowed to supply a receipt |
| `evidence-url` | empty | HTTPS URL of an evidence `.tar.gz` |
| `evidence-file` | empty | path to the evidence `.tar.gz` on the runner; takes precedence over `evidence-url` |
| `report` | `true` | publish the check run and sticky comment; `false` computes the verdict only |
| `require-evidence` | `true` | require a matching evidence archive; `false` allows digest only |
| `version` | `0.5.0` | out-of-band version to install; empty installs nothing |
| `source` | empty | local path to install instead; for development and the self-test |
| `python-version` | `3.12` | Python used by the verifier |
| `token` | `${{ github.token }}` | API token; see the permissions above |

Output: `verdict`, one of `verified`, `failed`, `unverified`, or
`not applicable`.

## What it does

1. Installs `out-of-band` at `version`, or from `source`.
2. Reads `allowed-signers` from the default branch through the contents API.
3. Resolves the receipt: the `receipt` input first, then trusted comments on
   `pr`.
4. Verifies the signature and the bindings.
5. Fetches the evidence archive, if any, and compares the digest.
6. Publishes a check run, a sticky comment, and a step summary. The evidence
   manifest goes into the summary and the archive becomes the `oob-evidence`
   artifact.

Each step is fail-soft: a failed verification becomes a published
`unverified`, not a crashed job. Only a tool error (exit 3) leaves no check.

## Waiting for the operator

The action does not block or poll. Each event is a new run:

1. The pull request opens. The workflow runs, finds no receipt, and publishes
   `unverified`.
2. The operator runs the job on the restricted machine and posts the receipt as
   a comment.
3. `issue_comment` runs the workflow again.
4. The action finds the block whose `commit` and `job` match, verifies it, and
   publishes a check with the same name. Branch protection sees the new result.

## Minimal setup

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
  verify:
    if: >
      github.event_name == 'pull_request_target' ||
      (github.event_name == 'issue_comment' &&
       github.event.issue.pull_request != null &&
       contains(github.event.comment.body, '<!-- receipt:v1 -->'))
    runs-on: ubuntu-latest
    steps:
      - id: context
        env:
          GH_TOKEN: ${{ github.token }}
          EVENT: ${{ github.event_name }}
          PR: ${{ github.event.pull_request.number || github.event.issue.number }}
        run: |
          if [ "$EVENT" = "pull_request_target" ]; then
            commit="${{ github.event.pull_request.head.sha }}"
          else
            commit="$(gh api "repos/$GITHUB_REPOSITORY/pulls/$PR" --jq .head.sha)"
          fi
          echo "pr=$PR" >> "$GITHUB_OUTPUT"
          echo "commit=$commit" >> "$GITHUB_OUTPUT"

      - uses: Oaklight/out-of-band@<full-sha> # v0.5.0
        with:
          pr: ${{ steps.context.outputs.pr }}
          commit: ${{ steps.context.outputs.commit }}
          job: bench-smoke
          check-name: receipt-verified
          trusted-authors: your-login
```

The snippet shows the gate wiring only. Evidence is required by default, so
add `evidence-url` or `evidence-file`, or set `require-evidence: false`.

## Safety notes

- Under `pull_request_target`, never check out or run pull request code. The
  action reads `allowed_signers` from the default branch through the API, so a
  pull request cannot change its own trust root.
- Pin `uses:` by full commit SHA in a real gate. A tag can move.
- The caller's `permissions` are the ceiling. The action cannot add
  `checks: write` if the job did not grant it.
- The action installs the CLI from PyPI at `version`; leave `source` empty
  outside this repository's self-test.
- Evidence is required by default. See [Evidence](../concepts/evidence.md) for
  the three sources and the token rule.

## Copy-ready examples

[`examples/`](../../../examples/README.md) has complete workflows:

- [pr-comment-gate.yml](../../../examples/pr-comment-gate.yml): a pull request
  gate with a policy job;
- [manual-dispatch.yml](../../../examples/manual-dispatch.yml): a maintainer
  pastes the receipt;
- [hardware-evidence.yml](../../../examples/hardware-evidence.yml): a GPU run
  plus an evidence bundle;
- [multi-job.yml](../../../examples/multi-job.yml): two jobs on one commit;
- [path-gate.yml](../../../examples/path-gate.yml): require a receipt only for
  changes under `patches/`;
- [reuse-local-run.yml](../../../examples/reuse-local-run.yml): verify a run
  that already happened elsewhere.
