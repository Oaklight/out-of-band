# Get started

[English](start.md) | [中文](../zh/start.md)

This page takes you from an empty machine to a receipt you can verify locally.
Wiring it into a repository is the next step, and the [action](reference/action.md)
and [reusable workflow](reference/workflow.md) pages cover both carriers.

## What you need

- Python 3.10 or newer.
- OpenSSH 8.0 or newer, for `ssh-keygen -Y sign`.
- A git clone that contains the commit you want to attest.

The package has no runtime dependencies.

```bash
pip install out-of-band
oob --version
```

The single-file build is on the release page as `oob-<version>.pyz`. It needs
only Python, which makes it the usual choice for a host that cannot reach PyPI.
See [Air-gapped hosts](guides/air-gapped.md).

## Make a key

```bash
ssh-keygen -t ed25519 -N "" -C "ci operator" -f ~/.ssh/out-of-band
```

`ssh-keygen -Y sign` reads the key file directly and does not use `ssh-agent`.
An empty passphrase is convenient for unattended runs; a passphrase is fine
when an operator is present to type it. Either way the private key stays on the
operator machine with mode `0600`.

Put the public key in the consumer repository as `.github/allowed_signers`:

```text
operator ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... ci operator
```

The first field is a principal you choose. It is a label in the signature, not
a GitHub login.

## Sign one commit

`--commit` takes a full 40-character SHA that exists in the local clone. The
tree is read from the commit, not from the working tree.

```bash
cd /path/to/repo
mkdir -p ./evidence
./run-the-check.sh 2>&1 | tee ./evidence/run.log

oob sign \
  --job smoke \
  --commit "$(git rev-parse HEAD)" \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/out-of-band \
  --repo owner/name \
  --out receipt.md
```

That writes one block: an HTML marker, one line of JSON, and an SSH signature.
The block is the receipt. The evidence directory is not uploaded; the receipt
records a digest of it.

Useful options:

| Option | Effect |
| --- | --- |
| `--repo owner/name` | the repository the receipt names; defaults to `origin` |
| `--claims k=v` | a small public fact to carry, repeatable |
| `--claims evidence_url=https://...` | sign the location of the evidence archive |
| `--output-file <file>` | carry up to 4 KiB of the check's output in the receipt |
| `--allow-dirty` | sign anyway when the worktree has uncommitted changes |

A dirty worktree is refused by default because the receipt binds the commit,
not the files on disk.

## Check it locally

```bash
oob verify \
  --block receipt.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/name \
  --commit "$(git rev-parse HEAD)" \
  --expect-job smoke
```

Exit codes are the result:

| Exit | Meaning |
| --- | --- |
| `0` | valid receipt, `result: pass` |
| `1` | valid receipt, `result: fail` |
| `2` | no receipt, or a receipt that does not verify |
| `3` | the tool could not run |

`--json` prints one machine-readable line. The exit code remains authoritative.

## Make the comment readable

A raw block is hard to read in a pull request. `oob render` turns it into a
Markdown table and keeps the exact signed bytes in a collapsed section:

```bash
oob render --block receipt.md --out comment.md
```

The table is presentation. A verifier ignores it and reads only the block.

## Package the evidence

```bash
oob pack --evidence-dir ./evidence --out evidence.tgz
```

`oob pack` writes a deterministic archive and prints the file count and digest.
Unpacking it reproduces the digest that `oob sign` already put in the receipt.
The verifier can then fetch the archive, recompute the digest, and keep it as a
run artifact.

## Put it in a repository

Choose one carrier:

- the [action](reference/action.md) runs as a step inside a job you already
  have;
- the [reusable workflow](reference/workflow.md) runs as its own job with its
  own timeout, concurrency, and permissions.

Both publish a check run with a name you choose. Require that name in branch
protection.

## Where to go next

- [Receipts](concepts/receipt.md) explains every field and binding.
- [Evidence](concepts/evidence.md) covers transport, limits, and retention.
- [States](concepts/states.md) explains why `unverified` is not `failed`.
