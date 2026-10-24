# Documentation

[English](README.md) | [中文](../zh/README.md)

Some jobs cannot run on GitHub: a benchmark on a rented GPU box, a patch smoke
test on a workstation, a training run inside a lab network. Out-of-band lets the
machine that ran the job sign a short claim, and lets GitHub verify it and
publish a check run. It also covers jobs that could run on CI but already ran somewhere else, where re-running is slow, flaky, or expensive.

Pick the page that matches what you are doing.

Prefer a visual walkthrough? [Take the guided tour](https://oaklight.github.io/out-of-band/).

| If you want to | Read |
| --- | --- |
| Block a PR until a patch has been tested | [Patch gate](scenario-patch-gate.md) |
| Record a benchmark or model run against a commit | [Hardware run](scenario-hardware-run.md) |
| Attest pushes to a branch, with no PR involved | [Branch gate](scenario-branch-gate.md) |
| Cover several machines or jobs | [Multiple jobs](scenario-multi-job.md) |
| Use the verifier as a step instead of a job | [The action](action.md) |
| Sign on a host with no outbound network | [Air-gapped hosts](offline.md) |
| Generate, rotate, or debug keys | [Operations](operations.md) |
| See the evidence from the self-test runs | [Validation](validation.md) |
| How this compares to Sigstore, attestations, and prior art | [Prior art](prior-art.md) |

## The shape they share

Every setup has the same three parts.

1. **A receipt.** One line of JSON and an SSH signature, produced by the
   operator on the machine that ran the job with `oob sign`. No network,
   no GitHub credential.
2. **A verifier.** The workflow or action checks the signature against
   `allowed_signers` read from the default branch, then binds the repository,
   commit, tree, and job.
3. **A check run.** GitHub publishes the verdict on the commit. Branch
   protection matches the check by name.

The states are distinct and stay that way:

| State | Meaning | Who acts |
| --- | --- | --- |
| `verified` | a valid signature over a passing claim | the merge can proceed |
| `failed` | a valid signature over a failing claim | fix the job, sign again |
| `unverified` | no usable receipt, a bad signature, or evidence that does not match | the operator |
| `not applicable` | no receipt was required for this change | nobody |

`unverified` is not a softer `failed`. It means the gate could not tell, so it
asks a human instead of guessing.

## Before wiring anything

- Pin the workflow or action by full commit SHA. A tag can move.
- Put `allowed_signers` in `.github/` on the default branch. That file is the
  trust root, and a PR cannot change it for itself.
- Choose `check-name` once. Branch protection matches the string, so renaming
  it silently changes what is protected.
