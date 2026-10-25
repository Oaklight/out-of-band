# Operations

[English](operations.md) | [中文](../zh/operations.md)

Keys, releases, and what to do when a verdict is not what you expected. The
model behind the trust root is in [Trust](concepts/trust.md); this page is the
runbook.

## Generate a key

```bash
ssh-keygen -t ed25519 -f ~/.ssh/out-of-band -C "out-of-band operator"
chmod 600 ~/.ssh/out-of-band
```

`ssh-keygen -Y sign` reads the key file directly and does not consult
`ssh-agent`. A passphrase means an interactive prompt, which is fine when an
operator is present and impossible in an unattended job.

The public key goes into `.github/allowed_signers` on the default branch:

```text
operator ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... out-of-band operator
```

The principal is a label you choose. It is not tied to a GitHub login.

## Change the trust root

The verifier reads `allowed_signers` from the default branch, and checks out
that branch on purpose. A pull request cannot add a key that would authenticate
its own receipt. Treat a change to this file as a policy change and review it
like one.

Removing a key does not only stop future receipts. Receipts it signed become
unverifiable, including ones already posted. If old attestations still matter,
keep the key listed and add a new one beside it.

## Rotate a key

1. Add the new public key to `allowed_signers` and merge.
2. Switch the operator machine to the new private key.
3. After the last receipt signed with the old key is no longer needed, remove
   the old key in another pull request.

Two keys can be listed at once; the verifier does not distinguish them.

## Add an operator

Add their public key to `allowed_signers`. If the caller sets
`trusted-authors`, also add their GitHub login. These are two separate gates:
who may post the comment, and whose signature counts.

## Releases and pinning

Consumers pin the action or workflow by full commit SHA:

```yaml
uses: Oaklight/out-of-band@<full-sha> # v0.5.0
```

The pin decides which verifier code runs. It does not decide which keys are
trusted; that is the caller's `allowed_signers`.

When a release changes the schema or the CLI, update the pin in a reviewed pull
request. A v2 verifier still reads v1 receipts, so a consumer is never forced
to re-sign old commits.

## Troubleshooting

Start with the run, not the check. The step summary carries the state, the
code, the source, and the commit. The check's output repeats the claims.

| State | Code | What it means |
| --- | --- | --- |
| `unverified` | `E_NO_BLOCK` | no trusted comment carries a receipt |
| `unverified` | `E_WRONG_COMMIT` | receipts exist, none for this commit |
| `unverified` | `E_WRONG_JOB` | receipts for this commit name another job |
| `unverified` | `E_BAD_SIGNATURE` | key not listed, or the bytes changed after signing |
| `unverified` | `E_WRONG_TREE` | the commit's tree does not match the signed tree |
| `unverified` | `E_MULTI_BLOCK` | two different receipts for the same commit and job |
| `unverified` | `E_EVIDENCE_MISMATCH` | the bundle does not hash to the signed digest |
| `unverified` | `E_NO_EVIDENCE` | evidence is required and no archive was supplied |
| `failed` | `OK` | the receipt is valid and says `result: fail` |
| `not applicable` | `OK` | the caller set `required: false` |

`failed` is not an error. It is a valid receipt reporting a failing job; the
check is red because the claim itself is negative.

Reproduce a verdict locally:

```bash
oob verify \
  --block receipt.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/repo \
  --commit <sha> \
  --expect-job <job>
```

The exit code is the verdict: 0 pass, 1 valid fail, 2 absent or invalid, 3 tool
error. The workflow maps 0 to `success`, and both 1 and 2 to `failure`; the
summary says which one it was. The full code table is in
[CLI](reference/cli.md#error-codes).

## Timing

Nothing waits for the operator. The verify job is triggered by an event and
finishes in seconds; a receipt may arrive hours or days after the run it
attests. A receipt has no TTL and is bound to a commit, so re-signing the same
commit produces another valid receipt rather than replacing the old one.

The only timeouts are local: 5 minutes for the reusable workflow's job, and 120
seconds for an evidence download. The action inherits the caller's job timeout.

## Evidence problems

- The URL must be reachable from the runner and must not need a browser
  session. A private object store needs a signed URL.
- The bundle must be a `.tar.gz` from `oob pack`, or have the same shape: no
  absolute paths, no `..`, no links, no special files.
- The digest covers paths and file contents, not archive bytes, so repacking is
  safe; changing a file is not.
- Anything over 50 MiB is rejected before extraction.
- Evidence that fails these checks turns a passing receipt into
  `E_EVIDENCE_MISMATCH` and `failure`. It does not fall back to digest only.

See [Evidence](concepts/evidence.md) for the three sources and the retention
rules.
