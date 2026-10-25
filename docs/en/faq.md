# FAQ

[English](faq.md) | [中文](../zh/faq.md)

## Why not run a self-hosted runner on that machine?

Use one if it fits. It needs a persistent outbound connection, a GitHub
credential on the host, and it executes workflow code from the repository,
which is a serious attack surface for a public repository. Ephemeral rentals
and scheduler-managed login nodes usually fit none of that.

## Why not put a token on the machine and post a status?

A long-lived credential then lives on the machine you wanted to keep clean. A
personal access token can create commit statuses but not check runs, and a
status is a label: nothing binds it to the evidence, the tree, or the job. A
receipt needs no credential, and the signature covers the claim itself.

## Why not just run the test in CI?

If a hosted runner can run it, do that. Out-of-band is the fallback for work
that cannot move.

## Why not approve by hand with a comment?

"LGTM" names no commit, no job, and no evidence, and it can be edited or
deleted. A receipt is machine-checked, binds one commit and one evidence
digest, and stays verifiable.

## Why not upload the log somewhere and link it?

Anyone can upload anything, and a link proves nothing about the commit.
Evidence is checked here: when it is supplied, the bundle is re-hashed against
the signed digest before it is kept.

## Why not Sigstore or GitHub artifact attestations?

Use them when the job runs in Actions. The workflow's OIDC identity is what
signs. A machine outside Actions has no such identity, and keyless signing
needs Fulcio and Rekor. Sigstore can sign a blob offline with a key, but the
GitHub-side gate is still yours to build: who may sign, for which commit, and
over what evidence. Out-of-band is that gate.

## Why not in-toto or SLSA?

They describe build provenance and supply-chain steps, and in-toto is the
closest in spirit. Both are more expressive and need a layout and a verifier.
A receipt is an operator attestation, not a builder-identity claim, and the
project does not claim a SLSA level. See [Prior art](prior-art.md).

## Does a receipt prove the job ran?

No. It proves that the holder of a listed key signed a statement naming a
repository, commit, tree, job, result, and evidence digest. Whether the job ran
and whether the evidence is truthful are outside the signature. See
[Trust](concepts/trust.md).

## What if the operator machine is compromised?

A stolen key can sign any claim. Pinning the tree limits reuse after a rewrite,
and evidence hashes limit substitution, but they do not detect a compromised
host. Rotate the key if you suspect it.

## Does a receipt expire?

No. It binds a commit, not a moment. `issued_at` is recorded, not enforced. If
policy needs a recent run, enforce that outside the gate.

## What happens after a force-push?

The commit is still reachable by SHA, and its check stays with it. A branch that
no longer contains the commit will not show it. Sign the new commit; a receipt
never transfers.

## Can several jobs or machines attest one commit?

Yes. Each receipt carries its own `job`, and collection filters by commit and
job, so several receipts can coexist. See
[Multiple jobs](guides/multi-job.md).

## Where does the evidence live?

On the operator side, by default. The run keeps a copy as the `oob-evidence`
artifact for the repository's Actions retention. The durable record is the
receipt comment. See [Evidence](concepts/evidence.md).

## Is there a server, an account, or a transparency log?

No. The tool has no service component. Keys live in the repository, signatures
are checked locally or in the workflow, and nothing is registered anywhere.

## Does it work outside GitHub?

The receipt format and the CLI are forge-agnostic. The verifier carriers are
GitHub-specific. Nothing stops another forge from checking the same block with
`oob verify`.

## Why SSH keys?

OpenSSH is already installed on the machines in question, `ssh-keygen -Y sign`
is a stock command, and `allowed_signers` is a plain text trust root that a
repository can review. No new key format, daemon, or PKI.

## Windows?

The CLI is pure Python and runs on Windows. The verifier carriers use
`ubuntu-latest`. The zipapp has no shebang, so run it as
`python oob-<version>.pyz`. See [Air-gapped hosts](guides/air-gapped.md).

## Can I use it without evidence?

Yes: set `require-evidence: false`. The receipt still binds the evidence
digest, but no archive is fetched or uploaded. The summary says `digest only`.

## Can I test the gate without publishing a check?

Set `report: false`. The verdict is computed and written to the step summary
and outputs, but no check run or comment is created. That is how this
repository's self-test runs its negative cases.
