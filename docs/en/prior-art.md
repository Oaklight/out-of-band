# Prior art and alternatives

[English](prior-art.md) | [中文](../zh/prior-art.md)

Out-of-band sits in a narrow gap. These tools solve adjacent problems, and
several are a better choice when their conditions hold.

## The mechanism is old

Jenkins, Buildkite, and CircleCI have reported results from outside GitHub
through commit statuses and the Checks API for years. Posting a verdict is not
new.

The delta is the receipt: one signature over a claim bound to repository,
commit, tree, job, and an evidence digest, verified by a workflow that reads
`allowed_signers` from the default branch. The operator host needs no GitHub
credential, and the result has four states rather than two.

## GitHub artifact attestations

`actions/attest-build-provenance` and `gh attestation verify` produce and check
Sigstore-backed provenance for artifacts built in a workflow. The identity
comes from the workflow's OIDC token, and GitHub stores the attestation.

They are the right tool when the job runs in Actions. A job on an HPC login node
or a rented GPU has no workflow identity to present. That is where out-of-band
fits.

## Sigstore, keyless

Keyless signing gets a short-lived certificate from Fulcio bound to an OIDC
identity and records the signature in Rekor. Both need network access and an
issuer. The host in the target scenario has neither.

Sigstore can sign a blob with a key offline, and that part overlaps. What it
does not provide is the GitHub-side policy: which key may speak for this
repository, which commit and evidence the claim covers, and what blocks a
merge. That policy layer is most of this tool.

Out-of-band has no transparency log. Its durable record is the pull request
comment; the evidence stays with the operator unless a bundle is supplied.

## SLSA and provenance frameworks

SLSA describes build provenance and levels. A receipt is an operator
attestation, not a builder-identity claim. Out-of-band does not make a SLSA
level and does not claim one.

in-toto is the closest in spirit: signed statements about supply-chain steps,
with a layout describing who may attest what. It is more expressive, and it
needs a layout and a verifier. Out-of-band deliberately has neither.

## Reusing a run that already happened

The second reason to use a receipt has weaker prior art. The usual options are
to re-run the job in CI and accept the cost, to trust a pasted log, or to
approve by hand. None of them binds the result to a commit and an evidence
digest. This is the same mechanism as the off-CI case; only the reason differs.

## Prior art in the same niche

These were design references, not dependencies. Credit where it is due:

- [`fredericrous/attest`](https://github.com/fredericrous/attest): `ssh-keygen`
  plus `allowed_signers`, tree binding, refusing a dirty worktree. It is
  deliberately fail-open, because its purpose is skipping redundant work rather
  than blocking a merge.
- [`Praxso/attested`](https://github.com/Praxso/attested): the receipt /
  verify-check / evidence-digest vocabulary, and the two-check idea (one for
  humans, one required). Its keyless signing ties it to Actions.
- [`AdriaBA/veriforge-attest`](https://github.com/AdriaBA/veriforge-attest):
  early and unlicensed; nothing was borrowed.
- [`LouisBrunner/checks-action`](https://github.com/LouisBrunner/checks-action):
  idiomatic use of the Checks API.

## When to use something else

- The job can run in Actions: use a hosted runner, and artifact attestations if
  you need provenance.
- The machine can run a runner and you control what executes there: a
  self-hosted runner is simpler than a receipt.
- You need a transparency log or a verifiable build identity: Sigstore and
  in-toto are the right layer.
- You need an approval, not evidence: a review or an environment rule is
  enough.
- Re-running the job is cheap and reproducible: just re-run it.

Out-of-band is for the remaining case: a required check, a job that runs where
GitHub cannot reach or has already run elsewhere, and no credential on that
machine.
