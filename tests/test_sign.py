from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from outboard.errors import OutboardError
from outboard.sign import sign


def extract(block: str) -> tuple[str, str]:
    lines = block.split("\n")
    assert lines[0] == "<!-- receipt:v1 -->"
    assert lines[1] == "```json"
    payload = lines[2]
    assert "\n" not in payload
    assert lines[3] == "```"
    assert lines[4] == "```ssh-signature"
    end = lines.index("```", 5)
    signature = "\n".join(lines[5:end])
    return payload, signature


def sign_block(root: Path, key: Path, evidence: Path, **overrides) -> str:
    params = {
        "job": "smoke",
        "commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "result": "pass",
        "evidence_dir": str(evidence),
        "key": str(key),
    }
    params.update(overrides)
    return sign(**params)


def test_block_shape_and_ssh_verification(
    repo: Path, keypair: Path, evidence: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(repo)
    block = sign_block(repo, keypair, evidence)
    payload, signature = extract(block)

    receipt = json.loads(payload)
    assert receipt["schema"] == "receipt/v1"
    assert receipt["repo"] == "acme/widget"
    assert receipt["result"] == "pass"
    assert receipt["job"] == "smoke"
    assert receipt["evidence"]["count"] == 2
    assert receipt["claims"] == {}

    allowed = tmp_path / "allowed_signers"
    allowed.write_text(f"operator {keypair.with_suffix('.pub').read_text().strip()}\n")
    sig_file = tmp_path / "block.sig"
    sig_file.write_text(signature + "\n")
    proc = subprocess.run(
        [
            "ssh-keygen",
            "-Y",
            "verify",
            "-f",
            str(allowed),
            "-I",
            "operator",
            "-n",
            "receipt",
            "-s",
            str(sig_file),
        ],
        input=payload.encode(),
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr.decode()


def test_receipt_binds_commit_and_tree(
    repo: Path, keypair: Path, evidence: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    payload, _ = extract(sign_block(repo, keypair, evidence))
    receipt = json.loads(payload)
    assert receipt["commit"] == head
    assert receipt["tree"] == tree


def test_dirty_worktree_is_refused(
    repo: Path, keypair: Path, evidence: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    (repo / "untracked.txt").write_text("x", encoding="utf-8")
    with pytest.raises(OutboardError) as caught:
        sign_block(repo, keypair, evidence)
    assert caught.value.code == "E_DIRTY_WORKTREE"

    block = sign_block(repo, keypair, evidence, allow_dirty=True)
    assert json.loads(extract(block)[0])["result"] == "pass"


def test_key_inside_evidence_is_refused(
    repo: Path, keypair: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(repo)
    directory = tmp_path / "evidence-with-key"
    directory.mkdir()
    (directory / "log.txt").write_text("x", encoding="utf-8")
    inner_key = directory / "signing-key"
    inner_key.write_bytes(keypair.read_bytes())
    with pytest.raises(OutboardError) as caught:
        sign_block(repo, inner_key, directory)
    assert caught.value.code == "E_KEY_IN_EVIDENCE"


def test_explicit_repo_overrides_remote(
    repo: Path, keypair: Path, evidence: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    payload, _ = extract(sign_block(repo, keypair, evidence, repo="other/place"))
    assert json.loads(payload)["repo"] == "other/place"


def test_claims_are_typed(
    repo: Path, keypair: Path, evidence: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    block = sign_block(
        repo,
        keypair,
        evidence,
        claims=["device_count=2", "capability=[7,0]", "flaky=false", "note=hello"],
    )
    claims = json.loads(extract(block)[0])["claims"]
    assert claims == {"device_count": 2, "capability": [7, 0], "flaky": False, "note": "hello"}


@pytest.mark.parametrize(
    "claim",
    ["device_count=null", "device_count=1.5", "Device=1", 'a={"b":1}', "a=1", "a=1.5"],
)
def test_bad_claims_are_usage_errors(
    repo: Path,
    keypair: Path,
    evidence: Path,
    monkeypatch: pytest.MonkeyPatch,
    claim: str,
) -> None:
    monkeypatch.chdir(repo)
    if claim == "a=1":
        claims = ["a=1", "a=2"]
    else:
        claims = [claim]
    with pytest.raises(OutboardError) as caught:
        sign_block(repo, keypair, evidence, claims=claims)
    assert caught.value.code == "E_USAGE"


def test_unsafe_integer_is_rejected(
    repo: Path, keypair: Path, evidence: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    with pytest.raises(OutboardError) as caught:
        sign_block(repo, keypair, evidence, claims=["n=9007199254740992"])
    assert caught.value.code == "E_CLAIMS_LIMIT"


def test_short_commit_is_rejected(
    repo: Path, keypair: Path, evidence: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    with pytest.raises(OutboardError) as caught:
        sign_block(repo, keypair, evidence, commit="abc1234")
    assert caught.value.code == "E_USAGE"
