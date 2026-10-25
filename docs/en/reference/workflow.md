# Reusable workflow

[English](workflow.md) | [中文](../../zh/reference/workflow.md)

`.github/workflows/verify.yml` runs the verifier as its own job. It declares
`workflow_call` only, so the caller owns the trigger.

Choose it when you want a separate job with its own timeout and concurrency, or
when you do not want the verifier's steps in your job. Choose the
[action](action.md) when verification belongs inside a job you already have.

## What it does

1. Checks out the caller's **default branch** with `persist-credentials: false`.
2. Installs `out-of-band` at the pinned `OOB_VERSION`.
3. Resolves the receipt from the `receipt` input or from trusted comments.
4. Verifies the signature and the bindings.
5. Fetches and checks the evidence archive.
6. Publishes a check run, a sticky comment, and a step summary.

The job runs on `ubuntu-latest`, times out after 5 minutes, and groups
concurrent runs by `check-name` and `commit` without cancelling an in-flight
run.

## Inputs

| Input | Type | Default | Meaning |
| --- | --- | --- | --- |
| `pr` | string | `"0"` | pull request for comment collection and the sticky comment; `0` disables both |
| `commit` | string | required | expected head SHA |
| `job` | string | required | expected job name |
| `required` | boolean | `true` | whether this change needs a receipt |
| `check-name` | string | `oob` | check run name |
| `receipt` | string | empty | receipt text; takes precedence over comments |
| `allowed-signers` | string | `.github/allowed_signers` | path in the caller repository |
| `trusted-authors` | string | empty | comma-separated logins allowed to supply a receipt |
| `evidence-url` | string | empty | HTTPS URL of an evidence `.tar.gz` |
| `evidence-file` | string | empty | path on the runner; takes precedence over `evidence-url` |
| `report` | boolean | `true` | publish the check run and sticky comment; `false` computes the verdict only |
| `require-evidence` | boolean | `true` | require a matching archive |
| `source-ref` | string | empty | internal: checkout ref for this repository's self-test; ignored elsewhere |

Output: `verdict`, one of `verified`, `failed`, `unverified`, or
`not applicable`.

`source-ref` exists so the tool repository can test unreleased code. A consumer
setting it gains nothing: the workflow reads it only when the caller is
`Oaklight/out-of-band`.

## Permissions

The caller must grant:

```yaml
permissions:
  contents: read
  checks: write
  pull-requests: write
```

No repository secrets are used. `GITHUB_TOKEN` is the only credential.

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
  policy:
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
          PR: ${{ github.event.pull_request.number || github.event.issue.number }}
        run: |
          commit="$(gh api "repos/$GITHUB_REPOSITORY/pulls/$PR" --jq .head.sha)"
          echo "pr=$PR" >> "$GITHUB_OUTPUT"
          echo "commit=$commit" >> "$GITHUB_OUTPUT"

      - id: paths
        env:
          GH_TOKEN: ${{ github.token }}
          PR: ${{ steps.context.outputs.pr }}
        run: |
          if gh api --paginate "repos/$GITHUB_REPOSITORY/pulls/$PR/files?per_page=100" \
               --jq '.[].filename' | grep -qE '^patches/'; then
            echo "requires=true" >> "$GITHUB_OUTPUT"
          else
            echo "requires=false" >> "$GITHUB_OUTPUT"
          fi

  verified:
    needs: policy
    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.5.0
    with:
      pr: ${{ needs.policy.outputs.pr }}
      commit: ${{ needs.policy.outputs.commit }}
      job: patch-smoke
      required: ${{ needs.policy.outputs.requires == 'true' }}
      check-name: patch-smoke-verified
      trusted-authors: your-login
```

The `policy` job resolves the head through the API because on `issue_comment`,
`github.sha` is the default branch, not the pull request head. The example
leaves out the evidence source; add `evidence-url` or `evidence-file` to the
call, or set `require-evidence: false`.

## Default-branch checkout

The workflow checks out the default branch on purpose. Checking out a pull
request would let the pull request supply its own `allowed_signers`. The only
repository file it reads is that one.

For the same reason, call it from `pull_request_target` or `issue_comment`, not
`pull_request`. Never check out or execute pull request code in the calling
workflow, which runs with a write token.

## Pinning

```yaml
uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.5.0
```

A full SHA is immutable. A tag can be moved. Keep the version in a comment and
let Dependabot open the bump pull request. See
[Operations](../operations.md#releases-and-pinning).

## Action or workflow

The action is a step, so it inherits the caller's permissions, timeout, and
concurrency; it can be used inside a job that does other work. The workflow is a
job, so its boundary is explicit and its settings are fixed. Both run the same
verifier and publish the same check.
