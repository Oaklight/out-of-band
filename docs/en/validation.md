# Operator-host validation

[English](validation.md) | [中文](../zh/validation.md)

Goal: show that the machine that runs the check and signs the receipt needs no
inbound path and holds no GitHub credential.

Recorded 2026-10-23 on a Debian 12 host with OpenSSH 9.2p1, Python 3.11, one
vCPU, and under 3 GiB of RAM. The host is referred to as **operator host**; no
hostname, address, username, or device identifier appears in this document.

## What was tested

| Check | Result |
|---|---|
| `outboard sign` inside an empty network namespace (`unshare -n`) | exit 0, valid block |
| `ssh-keygen -Y verify` of the literal payload, offline | exit 0 |
| GitHub credential on the host | none: no `gh` config, no `GH_TOKEN`/`GITHUB_TOKEN` in the environment |
| Inbound listener required by the flow | none; every step is a local read or an outbound HTTPS request |

## Procedure

Run as root on the operator host, in a throwaway directory.

```bash
WORK=$(mktemp -d)
mkdir -p "$WORK/repo" "$WORK/evidence/nested" "$WORK/keys"
cd "$WORK/repo"
git init -q -b main
git config user.email op@example.invalid
git config user.name operator
printf 'build ok\n' > build.log
git add build.log
git commit -qm candidate
git remote add origin git@github.com:acme/widget.git
COMMIT=$(git rev-parse HEAD)

printf 'run output\n' > "$WORK/evidence/run.log"
printf '{"passed":true}\n' > "$WORK/evidence/nested/result.json"
ssh-keygen -q -t ed25519 -N "" -f "$WORK/keys/op_key"

# No network namespace at all.
unshare -n env PYTHONPATH=/path/to/outboard/src python3 -m outboard.cli sign \
  --job smoke --commit "$COMMIT" --result pass \
  --evidence-dir "$WORK/evidence" --key "$WORK/keys/op_key" > "$WORK/block.md"

# Verify the literal bytes offline.
python3 - "$WORK" <<'PY'
import pathlib, re, subprocess, sys
work = pathlib.Path(sys.argv[1])
block = (work / "block.md").read_text()
payload, signature = re.search(
    r"```json\n(.*)\n```\n```ssh-signature\n(.*?)\n```", block, re.S
).groups()
(work / "payload.json").write_text(payload)
(work / "payload.sig").write_text(signature + "\n")
pub = (work / "keys" / "op_key.pub").read_text().strip()
(work / "allowed_signers").write_text(f"operator {pub}\n")
result = subprocess.run(
    ["ssh-keygen", "-Y", "verify", "-f", str(work / "allowed_signers"),
     "-I", "operator", "-n", "receipt", "-s", str(work / "payload.sig")],
    input=payload.encode(), capture_output=True,
)
print("verify exit:", result.returncode)
PY
```

The signed block and the verification both succeeded with networking disabled.

## What this does and does not prove

It proves the mechanism requires no inbound reachability and no GitHub
credential: signing is local, and verification is local.

It does not prove the host is otherwise locked down. The host may run unrelated
services with their own listeners; this test shows the receipt flow adds no
requirement for one. Delivering the receipt to GitHub needs one outbound HTTPS
request, or none at all when the operator pastes the block into the PR by hand.
