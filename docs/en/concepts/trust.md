# Trust

[English](trust.md) | [中文](../../zh/concepts/trust.md)

The trust root is a text file: `.github/allowed_signers` on the default branch.
Everything else follows from that choice.

## Who may sign

`allowed_signers` uses the OpenSSH format:

```text
operator ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... ci operator
```

- The first field is a principal. It is a label in the signature, not a GitHub
  login.
- One principal may list several keys, and several principals may exist.
- The verifier tries every principal and accepts a signature if any of them
  verifies it.
- Wildcard principals (`*`, `?`, `!`) are rejected. A trust root you cannot
  enumerate is not a trust root.

Who may *post* a receipt is a separate question. The workflow reads receipt
comments only from authors named in `trusted-authors`, or, when that input is
empty, from owners, members, and collaborators. An untrusted comment is
ignored, so a stranger cannot stall a gate by posting a marker.

## Why the file is read from the default branch

A pull request that could add its own key would authenticate its own receipt.
The reusable workflow checks out the default branch explicitly; the action
reads the file through the contents API at the default branch. Neither reads
`allowed_signers` from the pull request.

This is also why the caller uses `pull_request_target` or `issue_comment`
rather than `pull_request`: the gate must run default-branch code with a write
token. The trade-off is that this workflow must never check out or execute pull
request code.

## The private key

- It stays on the operator machine, mode `0600`.
- It never enters the repository, a receipt, an artifact, or a log.
- `ssh-keygen -Y sign` reads the file directly; `ssh-agent` is not involved.
- A passphrase is fine when someone is there to type it. Unattended signing
  uses an unencrypted key on a machine only the operator can log into.

The signer refuses to proceed when the key path is inside the evidence
directory, so the key's name and hash cannot enter the digest.

## Rotation and removal

1. Add the new public key to `allowed_signers` and merge.
2. Switch the operator machine to the new private key.
3. Remove the old key once no receipt that matters depends on it.

Removing a key does not only stop future receipts. It makes receipts that key
already signed unverifiable, including ones already posted. If old attestations
still matter, keep the key listed and add the new one beside it.

## What a receipt proves

That the holder of a listed private key signed these exact bytes, binding one
repository, commit, tree, job, and evidence digest.

It does not prove:

- that the job ran, or ran correctly;
- that the evidence matches the digest (the signer claimed a digest; comparing
  it with an uploaded archive is a separate check);
- that the signing machine was uncompromised;
- that the commit is what will merge (the tree is recorded so a rewritten
  commit does not match);
- that `issued_at` is accurate. It is self-claimed.

A receipt is an attestation by a key holder, not a proof of correctness.

## No expiry

A receipt binds a commit, not a moment. One signed weeks ago for the same
commit verifies exactly like one signed a minute ago. `issued_at` is recorded,
not enforced. If policy needs "this ran recently", enforce it outside the
mechanism, for example by requiring a fresh receipt when the environment
changes.

## What the verifier never does

- It never executes anything from the receipt.
- It never treats a claim as a command, a template, or a link.
- It never reads a repository file other than `allowed_signers`.
- It never sends the GitHub token to a host other than `api.github.com` and
  `github.com`.

The normative rules are in [SPEC.md](../../../SPEC.md) sections 3, 7, and 8.
