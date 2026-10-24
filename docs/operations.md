# Operations

[English](operations.md) | [中文](operations.zh.md)

Keys, trust, and what to do when a verdict is not what you expected.

## Generating a key

```bash
ssh-keygen -t ed25519 -f ~/.ssh/outboard -C "outboard operator"
chmod 600 ~/.ssh/outboard
```

`ssh-keygen -Y sign` reads the key file directly; it does not consult
`ssh-agent`. A passphrase means an interactive prompt, which is fine when a
person signs and impossible in an unattended job. Use an unencrypted key with
`0600` on a machine only the operator can log into, or sign interactively.

The public key goes into `.github/allowed_signers` on the default branch:

```
operator ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... outboard operator
```

The principal before the key is a label of your choosing. It is not tied to a
GitHub login.

## The trust root

The verifying workflow reads `allowed_signers` from the default branch, and
checks out that branch on purpose. A pull request cannot add a key that would
authenticate its own receipt. Changing the file is a policy change; review it
like one.

Removing a key does not only stop future receipts: receipts it signed become
unverifiable, including ones already posted. If old attestations still matter,
keep the key listed and add a new one beside it.

## Rotation

1. Add the new public key to `allowed_signers` and merge.
2. Switch the operator machine to the new private key.
3. After the last receipt signed with the old key is no longer needed, remove
   the old key in another pull request.

Two keys can be listed at once; the verifier does not distinguish them.

## Adding an operator

Add their public key to `allowed_signers`. If the workflow sets
`trusted-authors`, also add their GitHub login. These are two separate gates:
who may post the comment, and whose signature counts.

## Releases and pinning

Consumers pin `uses: Oaklight/outboard/.github/workflows/verify.yml@<sha>`. The
workflow reads `allowed_signers` from the caller repository, so the pin decides
which verifier code runs, not which keys are trusted.

When a new version changes the schema or the CLI, publish it, update the pin in
a reviewed pull request, and keep the old version working for at least one
release. A v2 verifier still reads v1 receipts.

## Troubleshooting

Start with the run, not the check. The step summary carries the state, the code,
the source, and the commit. The check's own output repeats the claims.

| Verdict | Code | What it means |
| --- | --- | --- |
| unverified | `E_NO_BLOCK` | no trusted comment carries a receipt |
| unverified | `E_WRONG_COMMIT` | receipts exist, none for this commit |
| unverified | `E_WRONG_JOB` | receipts for this commit name another job |
| unverified | `E_BAD_SIGNATURE` | key not listed, or the bytes changed after signing |
| unverified | `E_WRONG_TREE` | the commit's tree does not match the signed tree |
| unverified | `E_MULTI_BLOCK` | two different receipts for the same commit and job |
| unverified | `E_EVIDENCE_MISMATCH` | the bundle does not hash to the signed digest |
| unverified | `E_TOO_MANY_COMMENTS` | more than 5000 comments; exit 3 |
| failed | — | the receipt is valid and says `result: fail` |
| not applicable | `OK` | the caller set `required: false` |

`failed` is not an error. It is a valid receipt reporting a failing job; the
check is red because the claim itself is negative.

To reproduce a verdict locally:

```bash
outboard verify \
  --block receipt.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/repo \
  --commit <sha> \
  --expect-job <job>
```

Exit codes: 0 pass, 1 valid fail, 2 absent or invalid, 3 usage or internal. The
workflow maps these to `success`, `failure`, and `action_required`.

## Timing

Nothing waits for the operator. The verify job is triggered by an event and
finishes in seconds; a receipt may arrive hours or days after the run it
attests. A receipt has no TTL and is bound to a commit, so re-signing the same
commit produces another valid receipt rather than a new one replacing the old.

The only timeouts are local: 5 minutes for the verify job, 120 seconds for the
evidence download.

## Evidence problems

- The URL must be reachable from the runner and must not need a browser
  session. A private object store needs a signed URL.
- The bundle must be a `.tar.gz` from `outboard pack`, or have the same shape:
  no absolute paths, no `..`, no links, no special files.
- The digest covers paths and file contents, not archive bytes, so repacking is
  safe; changing a file is not.
- Anything over 50 MiB is rejected before extraction.
- Evidence that fails these checks turns a passing receipt into
  `E_EVIDENCE_MISMATCH` and `action_required`. It does not fall back to
  "digest only".
