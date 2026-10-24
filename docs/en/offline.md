# Air-gapped operator hosts

[English](offline.md) | [中文](../zh/offline.md)

HPC login nodes often have no outbound network, no route to PyPI, and no GitHub
credential. The flow still works; only the transport is manual.

Nothing in `sign`, `pack`, or `verify` opens a socket. The signature covers
local bytes, and `issued_at` comes from the host clock, so an unsynchronized
clock changes a timestamp, not validity.

## Who carries what

`out-of-band` implements no transport and opens no socket. A receipt is a signature
over bytes, so any channel that moves bytes works, and the channel does not have
to be trusted: alter the bytes and verification fails. Adding SSH to the tool
would mean owning credentials, host keys and bastion rules inside it, and would
still not fit every site.

The target machine and the signing machine do not have to be the same. A receipt
is the operator's assertion bound to an evidence digest, not a statement produced
by the host. The usual split is:

1. Run the job where it has to run, and have it write a run directory with the
   evidence (logs, outputs, measurements).
2. Bring the evidence out.
3. Sign where the private key lives.

### Keep the key off the cluster

Preferred. The cluster needs no key, no credential and no install; it only writes
a directory. Pull it to your workstation and sign there:

```bash
ssh hpc 'tar -C ~/runs/1234 -cf - .' | tar -C ./evidence -xf -
oob sign --job bench-smoke --commit <sha> --result pass \
  --evidence-dir ./evidence --key ~/.ssh/out-of-band --repo owner/name \
  --output-file ./check-output.txt > receipt.md
```

The claim still says what happened on the host; the signature says you stand
behind it, and the digest says exactly which bytes you are standing behind.

### If the signature must come from the host

Some policies want the key to stay inside the enclave. Then the host signs, and
only the output travels. In order of preference:

**Shared storage.** Login and compute nodes usually share `$HOME` or a scratch
filesystem. Let the job write `~/runs/<id>/`, sign from the login node, and pull
the result from your workstation. Nothing has to route back to the host.

**SSH pull.** Your workstation reaches the host (directly or through a bastion),
never the other way round:

```bash
ssh hpc 'cat ~/runs/1234/receipt.md' > receipt.md
ssh hpc 'cat ~/runs/1234/evidence.tgz' > evidence.tgz
```

`sign` writes its block to stdout, so it can also run remotely with the key on
the host:

```bash
ssh hpc 'oob sign --job bench-smoke --commit <sha> --result pass \
  --evidence-dir runs/1234 --key .ssh/out-of-band --repo owner/name' > receipt.md
```

**One-way physical transfer.** USB, a data diode, or an internal share from a
jump host. The procedure above is unchanged; only the `scp` becomes a copy.

### What the runner still needs

The workflow fetches `evidence-url` from GitHub's runner, not from your machine.
So the URL must be reachable from the internet-facing runner; a URL on the HPC's
internal network will not work. Upload the bundle from the connected side, then
dispatch or comment.

## Carry the tool in

One file is usually enough. Each release carries `oob-<version>.pyz`: a
zipapp holding the package and an entry point, needing only Python 3.11+.

```bash
scp oob-0.4.0.pyz host:
ssh host python3 oob-0.4.0.pyz --version
```

It behaves like the installed command, so every example below works with
`python3 oob-0.4.0.pyz` in place of `oob`. Run it as `./oob-0.4.0.pyz` and the
POSIX launcher picks the first Python 3.11+ it finds; if none exists it says so
instead of failing with a syntax error. Windows has no shebang, so use
`python oob-0.4.0.pyz`.

If the site prefers a normal install, the wheel is pure Python
(`py3-none-any`), so any 3.11+ interpreter can use it. On a connected machine:

```bash
pip download out-of-band==0.4.0 -d wheelhouse
```

Copy `wheelhouse/` over, then:

```bash
python3 -m venv ~/out-of-band
~/out-of-band/bin/pip install --no-index --find-links wheelhouse out-of-band==0.4.0
~/out-of-band/bin/oob --version
```

The wheel, sdist and zipapp are all on the release page, so they can be fetched
from a browser too.

## Carry the repository in

`sign` needs the commit to exist locally (`git cat-file -e <sha>^{commit}`). A
clone that only has the default branch is not enough for a PR head.

From a clone that has the PR ref:

```bash
git bundle create lab.bundle main <pr-branch>
```

Copy it, then on the host:

```bash
git clone lab.bundle work
cd work
git checkout <head-sha>
```

If the host already has the repository, fetch the bundle into it instead:

```bash
git fetch /path/to/lab.bundle <head-sha>
```

Pass `--repo owner/name` explicitly: a clone made from a bundle may have a
local path as `origin`, which cannot be turned into a repository name.

## Sign and pack

```bash
oob sign \
  --job bench-smoke \
  --commit <head-sha> \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/out-of-band \
  --repo owner/name \
  --output-file ./check-output.txt

oob pack --evidence-dir ./evidence --out evidence.tgz
```

No network, no credential, no daemon.

## Carry the result out

Copy the receipt and the bundle to a connected workstation:

```bash
scp host:receipt.md host:evidence.tgz .
```

Then either post the receipt as a PR comment, or run the gate manually:

```bash
gh workflow run receipt-gate.yml -f pr=5 -f commit=<head-sha> \
  -f receipt="$(cat receipt.md)" -f evidence-url=<https-url-to-evidence.tgz>
```

The evidence URL must be reachable from the **runner**, not from the HPC host.
Uploading the bundle to a repository evidence branch, a PR attachment, or an
internal object store all work. The workflow verifies the bundle against the
signed digest before keeping it.

## What this does not solve

- The receipt still has to be carried out by an operator or a one-way transfer.
  There is no outbound path from the host, by definition.
- Large raw logs should be curated before packing. The workflow caps a bundle
  at 50 MiB; the signed `output` is capped at 4 KiB.
- Key rotation still happens on the connected side, by editing
  `allowed_signers`.
