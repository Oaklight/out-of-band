# Scenario: test a patch before it merges

[English](scenario-patch-gate.md) | [中文](scenario-patch-gate.zh.md)

You have a `patches/` directory (or `src/`, or a firmware tree) whose changes
must be smoke-tested on real hardware. CI cannot run that test, so a person
runs it and signs the result.

## The workflow

Two jobs: `policy` decides whether this PR needs a receipt, `verified` calls the
reusable workflow.

```yaml
name: receipt gate

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  issue_comment:
    types: [created]

permissions:
  contents: read
  checks: write
  pull-requests: write

jobs:
  policy:
    # Re-run when a comment carries a receipt; ignore every other comment.
    if: >
      github.event_name == 'pull_request' ||
      (github.event_name == 'issue_comment' &&
       github.event.issue.pull_request != null &&
       contains(github.event.comment.body, '<!-- receipt:v1 -->'))
    runs-on: ubuntu-latest
    outputs:
      pr: ${{ steps.context.outputs.pr }}
      commit: ${{ steps.context.outputs.commit }}
      requires: ${{ steps.paths.outputs.requires }}
    steps:
      - name: Resolve the PR and its head
        id: context
        env:
          GH_TOKEN: ${{ github.token }}
          PR_NUMBER: ${{ github.event.pull_request.number || github.event.issue.number }}
        run: |
          commit="$(gh api "repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER" --jq .head.sha)"
          echo "pr=$PR_NUMBER" >> "$GITHUB_OUTPUT"
          echo "commit=$commit" >> "$GITHUB_OUTPUT"

      - name: Decide whether a receipt is required
        id: paths
        env:
          GH_TOKEN: ${{ github.token }}
          PR: ${{ steps.context.outputs.pr }}
        run: |
          if gh api --paginate "repos/$GITHUB_REPOSITORY/pulls/$PR/files?per_page=100" \
               --jq '.[].filename' | grep -qE '^(patches|firmware)/'; then
            echo "requires=true" >> "$GITHUB_OUTPUT"
          else
            echo "requires=false" >> "$GITHUB_OUTPUT"
          fi

  verified:
    needs: policy
    uses: Oaklight/outboard/.github/workflows/verify.yml@<full-sha>
    with:
      pr: ${{ needs.policy.outputs.pr }}
      commit: ${{ needs.policy.outputs.commit }}
      job: patch-smoke
      required: ${{ needs.policy.outputs.requires == 'true' }}
      check-name: patch-smoke-verified
      trusted-authors: your-login
```

The API call resolves the head for both triggers. On `issue_comment`,
`github.sha` is the default branch, not the PR head, so the event context cannot
be used directly.

What the inputs mean:

- `job` is the name inside the receipt. The operator must sign with the same
  string.
- `check-name` is what branch protection matches. Keep it unique per job.
- `required: false` turns an absent receipt into `not applicable` with a
  `success` conclusion, so a docs-only PR is not blocked.
- `trusted-authors` narrows who may supply a receipt. Without it, any owner,
  member, or collaborator qualifies.

## What the operator does

```bash
# 1. Get the exact commit that was pushed.
gh pr checkout 5            # or: git fetch origin pull/5/head:pr-5
git rev-parse HEAD          # 6e5b8a4...

# 2. Run the test and keep the evidence.
mkdir -p /tmp/evidence
./run-smoke.sh 2>&1 | tee /tmp/evidence/smoke.log

# 3. Sign. Runs offline; the key never leaves this machine.
outboard sign \
  --job patch-smoke \
  --commit "$(git rev-parse HEAD)" \
  --result pass \
  --evidence-dir /tmp/evidence \
  --key ~/.ssh/outboard \
  --repo owner/repo \
  --output-file /tmp/evidence/last-lines.txt \
  --out receipt.md

# 4. Deliver. A PR comment from a trusted account is the usual channel.
gh pr comment 5 --body-file receipt.md
```

`--output-file` is optional. It puts up to 4 KiB of text into the check's
foldable transcript, which is where a reviewer looks first. Do not put secrets
there; the check is public.

## What you replace

The workflow is a template, but only a few things are yours to set. Everything
inside `${{ }}` is evaluated by GitHub at run time; you do not fill it in.

| Placeholder | What it is |
| --- | --- |
| `<full-sha>` in `uses:` | the outboard commit you pin; copy it from the release page |
| `job:` | must equal the operator's `--job` |
| `check-name:` | the string branch protection matches, so keep it unique per job |
| `trusted-authors:` | optional; your GitHub login, or a comma-separated list |

If you copy the caller workflow from this page, nothing else needs editing.

## Write it once

Commit the caller workflow to the default branch once. A new pull request needs
a receipt, not a workflow change: `policy` resolves the head and the changed
paths at run time. Changing the pinned SHA is an upgrade you schedule, and
adding a platform means adding one caller job, once.

## What happens next

The comment triggers the workflow, because the marker in the block matches the
`policy` condition. The verifier reads the PR's comments, keeps the ones from
trusted authors, selects the block for the head commit and `patch-smoke`,
verifies the signature, and publishes `patch-smoke-verified`.

If the PR moves on with a new push, the old receipt no longer matches the head
and is ignored. Sign the new commit and post a new comment; nothing has to be
deleted.

## Where it goes wrong

| Symptom | Cause |
| --- | --- |
| `E_WRONG_COMMIT` | you signed the merge commit or an older head; check `git rev-parse HEAD` |
| `E_WRONG_JOB` | `--job` does not match the `job:` input |
| `E_BAD_SIGNATURE` | the key is not in `allowed_signers` on the default branch |
| `E_MULTI_BLOCK` | two different receipts for the same commit and job; delete one |
| the check is missing entirely | the workflow did not run; look at the Actions tab and the `if:` gate |

## Notes

- Do not check out the PR head in the verifying job. The workflow reads
  `allowed_signers` from the default branch on purpose.
- A fork PR gets a read-only token on `pull_request`. Use `issue_comment` as
  shown, or `pull_request_target`.
- Evidence is optional. Add `evidence-url` when the logs matter; see
  [Hardware run](scenario-hardware-run.md).
