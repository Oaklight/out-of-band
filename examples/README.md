# Examples

Complete caller workflows. Copy the closest one and change the placeholders.

| File | What it shows |
| --- | --- |
| [pr-comment-gate.yml](pr-comment-gate.yml) | A pull request gate: a policy job resolves the head, then the action verifies a receipt posted as a comment. |
| [manual-dispatch.yml](manual-dispatch.yml) | A maintainer pastes a receipt into a `workflow_dispatch` run. |
| [hardware-evidence.yml](hardware-evidence.yml) | A GPU run plus an evidence archive passed by URL. |
| [multi-job.yml](multi-job.yml) | Two jobs on one commit, using the action with a matrix. |
| [path-gate.yml](path-gate.yml) | Require a receipt only when the pull request touches `patches/`. |
| [reuse-local-run.yml](reuse-local-run.yml) | Publish a check for a run that already happened outside GitHub. |

## Before you copy

- Replace `<full-sha>` or the tag with a full commit SHA and keep the version
  in a comment. A tag can move.
- Set `job` to the name the operator will pass to `oob sign --job`.
- Set `check-name` to the string you will require in branch protection.
- Set `trusted-authors` if anyone other than owners, members, and collaborators
  may post a receipt.
- Evidence is required by default. Supply `evidence-url` or `evidence-file`, or
  set `require-evidence: false`.

The reusable workflow takes the same inputs and is documented in
[reference/workflow.md](../docs/en/reference/workflow.md). The action's inputs
are in [reference/action.md](../docs/en/reference/action.md).

## Try one locally

`reuse-local-run.yml` is the smallest shape: the receipt arrives as a comment,
and the verifier does not run the job again. For a first experiment, use a
throwaway repository and a test key; do not reuse the key you plan to keep.
