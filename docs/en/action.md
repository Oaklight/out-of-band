# The action

The reusable workflow is a job; the action is a step. Both run the same
verifier and publish the same check run. The difference is who owns the wrapper.

Use the action when you want verification inside an existing job, when you want
to set triggers, permissions, and concurrency yourself, or when you found it on
Marketplace. Use the [reusable workflow](../../README_en.md#wiring-a-consumer)
when you want the verifier on its own runner with its own timeout and a
separate job boundary.

| | Action | Reusable workflow |
| --- | --- | --- |
| Called from | a step, `uses: Oaklight/out-of-band@v0.5.0` | a job, `uses: Oaklight/out-of-band/.github/workflows/verify.yml@<sha>` |
| Runner | the caller's job | its own `ubuntu-latest` job |
| Permissions | caller sets them | the workflow declares its own |
| Timeout, concurrency | caller sets them | built in |
| Marketplace | eligible | not eligible |

## What the caller has to supply

The action cannot declare any of these. They belong to the workflow that calls
it:

- the trigger, usually `pull_request_target` plus `issue_comment`
- `permissions: contents: read, checks: write, pull-requests: write`
- the token input, which defaults to `${{ github.token }}`
- a `check-name`, because branch protection matches that string
- the commit and job name the receipt must carry

## Inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `commit` | required | commit SHA the receipt must name |
| `job` | required | job name the receipt must carry |
| `pr` | `0` | pull request for comment collection and the summary; `0` disables both |
| `required` | `true` | whether this commit needs a receipt at all |
| `check-name` | `oob` | check run name |
| `receipt` | empty | receipt text; takes precedence over comments |
| `allowed-signers` | `.github/allowed_signers` | path in the caller repository, read from the default branch |
| `trusted-authors` | empty | comma-separated logins allowed to supply a receipt |
| `evidence-url` | empty | HTTPS URL of an evidence `.tar.gz` |
| `report` | `true` | publish the check run and sticky comment; `false` computes the verdict only |
| `require-evidence` | `true` | require a matching evidence archive; `false` allows digest only |
| `version` | `0.4.0` | out-of-band version to install; empty installs nothing |
| `source` | empty | local path to install instead; for development and the self-test |
| `python-version` | `3.12` | Python used by the verifier |
| `token` | `${{ github.token }}` | API token; see the permissions above |

The `verdict` output is one of `verified`, `failed`, `unverified`, or
`not applicable`.

## Waiting for the operator

The action does not block and poll. Each event is a new run:

1. The PR opens. The workflow runs, finds no receipt, and publishes
   `unverified`. The check does not pass.
2. The operator runs the job on the restricted machine and posts the signed
   receipt as a comment.
3. `issue_comment` runs the workflow again.
4. The action finds the block whose `commit` and `job` match, verifies the
   signature, and publishes a check with the same name. Branch protection now
   sees the new result.

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

      - uses: Oaklight/out-of-band@v0.5.0
        with:
          pr: ${{ steps.context.outputs.pr }}
          commit: ${{ steps.context.outputs.commit }}
          job: bench-smoke
          check-name: receipt-verified
```

## Safety notes

- Under `pull_request_target` the action never checks out or runs pull request
  code. It reads `allowed_signers` from the default branch through the API, so
  a PR cannot change its own trust root.
- Pin `uses:` by full commit SHA in a real gate. The tag in the example is
  readable, not immutable.
- The caller's `permissions` are the ceiling. The action cannot add `checks:
  write` if the job did not grant it.
- The action installs the CLI from PyPI at `version`; leave `source` empty
  outside the repository's own self-test.

## Copy-ready examples

The [`examples/`](https://github.com/Oaklight/out-of-band/tree/main/examples)
directory has complete workflows for each shape:

- [pr-comment-gate.yml](https://github.com/Oaklight/out-of-band/blob/main/examples/pr-comment-gate.yml): the gate above, with a policy job
- [manual-dispatch.yml](https://github.com/Oaklight/out-of-band/blob/main/examples/manual-dispatch.yml): a maintainer pastes the receipt
- [hardware-evidence.yml](https://github.com/Oaklight/out-of-band/blob/main/examples/hardware-evidence.yml): GPU run plus evidence bundle
- [multi-job.yml](https://github.com/Oaklight/out-of-band/blob/main/examples/multi-job.yml): two jobs on one commit
- [path-gate.yml](https://github.com/Oaklight/out-of-band/blob/main/examples/path-gate.yml): require a receipt only under `patches/`
- [reuse-local-run.yml](https://github.com/Oaklight/out-of-band/blob/main/examples/reuse-local-run.yml): verify a run that already happened elsewhere
