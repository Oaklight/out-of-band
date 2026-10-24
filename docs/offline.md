# Air-gapped operator hosts

HPC login nodes often have no outbound network, no route to PyPI, and no GitHub
credential. The flow still works; only the transport is manual.

Nothing in `sign`, `pack`, or `verify` opens a socket. The signature covers
local bytes, and `issued_at` comes from the host clock, so an unsynchronized
clock changes a timestamp, not validity.

## Carry the tool in

The wheel is pure Python (`py3-none-any`), so any Python 3.11+ interpreter can
use it.

On a connected machine:

```bash
pip download outboard==0.3.0 -d wheelhouse
```

Copy `wheelhouse/` to the host, then:

```bash
python3 -m venv ~/outboard
~/outboard/bin/pip install --no-index --find-links wheelhouse outboard==0.3.0
~/outboard/bin/outboard --version
```

The same wheel and sdist are attached to the GitHub release, so they can be
copied from a browser too.

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
outboard sign \
  --job bench-smoke \
  --commit <head-sha> \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/outboard \
  --repo owner/name \
  --output-file ./check-output.txt

outboard pack --evidence-dir ./evidence --out evidence.tgz
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

- The receipt still has to be carried out by a person or a one-way transfer.
  There is no outbound path from the host, by definition.
- Large raw logs should be curated before packing. The workflow caps a bundle
  at 50 MiB; the signed `output` is capped at 4 KiB.
- Key rotation still happens on the connected side, by editing
  `allowed_signers`.
