# Documentation

[English](README.md) | [中文](../zh/README.md)

Two kinds of jobs end up here:

- a job GitHub cannot run, because the hardware, the toolchain, the network, or
  the data is somewhere else;
- a job that already ran somewhere else, and repeating it in CI is slow,
  flaky, or gives a different answer.

In both cases the machine that ran the job signs a short claim, and a workflow
on GitHub verifies it and publishes a check. The machine needs no inbound path
and no GitHub credential.

Prefer a visual walkthrough? [Take the guided tour](https://oaklight.github.io/out-of-band/).

## Read by what you are doing

| If you want to | Read |
| --- | --- |
| Install it and sign your first receipt | [Get started](start.md) |
| Understand what a receipt binds | [Receipts](concepts/receipt.md) |
| Decide which key counts, and what the gate does not prove | [Trust](concepts/trust.md) |
| Attach logs or outputs to a receipt | [Evidence](concepts/evidence.md) |
| Understand the four verdicts | [States](concepts/states.md) |
| Look up a command or an exit code | [CLI](reference/cli.md) |
| Use the verifier as a step | [Action](reference/action.md) |
| Use the verifier as a job | [Reusable workflow](reference/workflow.md) |
| Block a PR until a patch has been tested | [Patch gate](guides/patch-gate.md) |
| Record a benchmark or model run against a commit | [Hardware run](guides/hardware-run.md) |
| Cover several machines or jobs | [Multiple jobs](guides/multi-job.md) |
| Attest pushes when no pull request exists | [Branch gate](guides/branch-gate.md) |
| Sign on a host with no outbound network | [Air-gapped hosts](guides/air-gapped.md) |
| Generate, rotate, or debug keys | [Operations](operations.md) |
| See the evidence from the self-test runs | [Validation](validation.md) |
| Compare with Sigstore, attestations, and prior art | [Prior art](prior-art.md) |
| Get a straight answer to a common objection | [FAQ](faq.md) |

## How the pieces fit

1. **A receipt.** One line of JSON and an SSH signature, produced by `oob sign`
   on the machine that ran the job. No network, no GitHub credential.
2. **A verifier.** A workflow or action checks the signature against
   `allowed_signers` read from the default branch, then checks the repository,
   commit, tree, and job.
3. **A check run.** GitHub publishes the verdict on the commit. Branch
   protection matches the check by name.

The repository implements the mechanism. The consumer owns the policy: which
paths need a receipt, which job name, which key, and whether the check is
required.

## Before wiring anything

- Pin the action or workflow by full commit SHA. A tag can move.
- Put `allowed_signers` in `.github/` on the default branch. That file is the
  trust root, and a pull request cannot change it for itself.
- Choose `check-name` once. Branch protection matches the string, so renaming
  it silently changes what is protected.
