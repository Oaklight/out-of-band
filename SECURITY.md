# Security policy

## Supported versions

Security fixes land on the latest release line. At the time of writing that is
0.5.x. Older versions may not receive a backport; the fix will be in the next
release.

## Report a vulnerability

Use GitHub's private vulnerability reporting on this repository
("Security" → "Report a vulnerability"). Do not open a public issue.

Include:

- the version (`oob --version`) and the carrier (CLI, action, or reusable
  workflow);
- the input that triggers the problem, reduced as far as possible;
- what an attacker gains, and what access they need to start.

You will get an acknowledgement, an assessment, and a fix or a reasoned
rejection. There is no bug bounty.

## In scope

- a signature that verifies when it should not, or a receipt whose fields are
  trusted before the signature does;
- a receipt that can crash the verifier, exhaust its memory, or make it execute
  something;
- path traversal, link following, or resource exhaustion while extracting an
  evidence archive;
- reading `allowed_signers` from anywhere other than the default branch;
- leaking the GitHub token to a host other than `api.github.com` and
  `github.com`;
- publishing a check or editing a comment under an identity or name the caller
  did not configure.

## Out of scope

- a compromised operator machine or a stolen private key. A receipt says the
  key holder signed the bytes; it cannot detect that the holder was tricked.
- a job that reports a result it did not earn. That is the attestation boundary
  described in [docs/en/concepts/trust.md](docs/en/concepts/trust.md).
- vulnerabilities in GitHub Actions, GitHub itself, or a third-party runner.
- the fact that evidence is visible to anyone who can read the run or its URL.
  Treat evidence like a CI log.

## Trust model

The short version: the trust root is `.github/allowed_signers` on the default
branch. The verifier checks one SSH signature over the literal JSON line, then
checks repository, commit, tree, and job against the caller's context. It never
executes receipt content and never reads another repository file.

The full statement, including what a receipt does not prove, is in
[Trust](docs/en/concepts/trust.md) and [SPEC.md](SPEC.md) §8.
