from __future__ import annotations

import json
from pathlib import Path

import pytest

from outboard.block import extract
from outboard.cli import main
from outboard.errors import OutboardError
from outboard.sign import sign
from outboard.verify import verify


def make_block(
    root: Path,
    key: Path,
    evidence: Path,
    directory: Path,
    result: str = "pass",
) -> tuple[Path, Path, str]:
    head = _git(root, "rev-parse", "HEAD")
    block = sign(
        job="smoke",
        commit=head,
        result=result,
        evidence_dir=str(evidence),
        key=str(key),
        repo="acme/widget",
    )
    block_path = directory / "block.md"
    block_path.write_text(block, encoding="utf-8")
    allowed = directory / "allowed_signers"
    allowed.write_text(f"operator {key.with_suffix('.pub').read_text().strip()}\n")
    return block_path, allowed, head


def _git(root: Path, *args: str) -> str:
    import subprocess

    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def compose(payload: str, signature: str = "x") -> str:
    return f"<!-- receipt:v1 -->\n```json\n{payload}\n```\n```ssh-signature\n{signature}\n```\n"


def run_verify(block: Path, allowed: Path, head: str, **overrides) -> dict:
    params = {
        "block_path": str(block),
        "allowed_signers": str(allowed),
        "repo": "acme/widget",
        "commit": head,
        "job": "smoke",
    }
    params.update(overrides)
    return verify(**params)


def test_valid_pass(
    repo: Path, keypair: Path, evidence: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    block, allowed, head = make_block(repo, keypair, evidence, tmp_path)
    result = run_verify(block, allowed, head)
    assert result == {
        "verdict": "pass",
        "code": "OK",
        "repo": "acme/widget",
        "commit": head,
        "job": "smoke",
    }


def test_valid_fail(
    repo: Path, keypair: Path, evidence: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    block, allowed, head = make_block(repo, keypair, evidence, tmp_path, result="fail")
    assert run_verify(block, allowed, head)["verdict"] == "fail"


def test_cli_exit_codes(
    repo: Path,
    keypair: Path,
    evidence: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(repo)
    block, allowed, head = make_block(repo, keypair, evidence, tmp_path)
    base = [
        "verify",
        "--block",
        str(block),
        "--allowed-signers",
        str(allowed),
        "--repo",
        "acme/widget",
        "--expect-job",
        "smoke",
        "--json",
    ]
    assert main(base + ["--commit", head]) == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "pass"

    assert main(base + ["--commit", "0" * 40]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "unverified"
    assert payload["code"] == "E_WRONG_COMMIT"


def _expect(block: Path, allowed: Path, head: str, code: str, **overrides) -> None:
    with pytest.raises(OutboardError) as caught:
        run_verify(block, allowed, head, **overrides)
    assert caught.value.code == code
    assert caught.value.exit_code == 2


def test_tampering_is_rejected(
    repo: Path, keypair: Path, evidence: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    block, allowed, head = make_block(repo, keypair, evidence, tmp_path)

    _expect(block, allowed, head, "E_WRONG_REPO", repo="other/place")
    _expect(block, allowed, head, "E_WRONG_COMMIT", commit="1" * 40)
    _expect(block, allowed, head, "E_WRONG_JOB", job="other")
    _expect(block, allowed, head, "E_WRONG_TREE", tree="2" * 40)

    text = block.read_text()
    payload, signature = extract(text)
    altered = payload.decode().replace('"acme/widget"', '"acm3/widget"')
    block.write_text(compose(altered, signature))
    _expect(block, allowed, head, "E_NO_PRINCIPAL")


def test_schema_failures(
    repo: Path, keypair: Path, evidence: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    block, allowed, head = make_block(repo, keypair, evidence, tmp_path)
    payload, signature = extract(block.read_text())

    receipt = json.loads(payload)
    receipt["extra"] = 1
    block.write_text(compose(json.dumps(receipt, separators=(",", ":")), signature))
    _expect(block, allowed, head, "E_UNKNOWN_FIELD")

    block.write_text(compose('{"schema":'))
    _expect(block, allowed, head, "E_BAD_JSON")

    block.write_text(compose('{"schema":"receipt/v1","schema":"receipt/v1"}'))
    _expect(block, allowed, head, "E_DUP_KEY")

    block.write_text('<!-- receipt:v1 -->\n```json\n{\n"a":1}\n```\n```ssh-signature\nx\n```\n')
    _expect(block, allowed, head, "E_MULTI_LINE")

    block.write_text(compose('{"a":"' + "x" * 17000 + '"}'))
    _expect(block, allowed, head, "E_TOO_LARGE")

    block.write_text("<!-- receipt:v1 -->\n```json\n{}\n```\n")
    _expect(block, allowed, head, "E_BAD_FENCE")

    block.write_text(compose(payload.decode(), "not-a-signature"))
    _expect(block, allowed, head, "E_BAD_SIGNATURE")


def test_multiple_markers_and_missing_block(
    repo: Path, keypair: Path, evidence: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    block, allowed, head = make_block(repo, keypair, evidence, tmp_path)
    text = block.read_text()

    block.write_text(text + "\n" + text)
    _expect(block, allowed, head, "E_MULTI_BLOCK")

    block.write_text("nothing here")
    _expect(block, allowed, head, "E_NO_BLOCK")


def test_stranger_key(
    repo: Path, keypair: Path, evidence: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    monkeypatch.chdir(repo)
    block, allowed, head = make_block(repo, keypair, evidence, tmp_path)
    stranger = tmp_path / "stranger"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(stranger)], check=True)
    allowed.write_text(f"operator {stranger.with_suffix('.pub').read_text().strip()}\n")
    _expect(block, allowed, head, "E_NO_PRINCIPAL")


def test_wildcard_principal_is_a_config_error(
    repo: Path, keypair: Path, evidence: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    block, allowed, head = make_block(repo, keypair, evidence, tmp_path)
    allowed.write_text(f"* {keypair.with_suffix('.pub').read_text().strip()}\n")
    with pytest.raises(OutboardError) as caught:
        run_verify(block, allowed, head)
    assert caught.value.code == "E_BAD_ALLOWED_SIGNERS"
    assert caught.value.exit_code == 3


def test_v2_receipt_with_output_verifies(
    repo: Path, keypair: Path, evidence: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    head = _git(repo, "rev-parse", "HEAD")
    output = tmp_path / "output.txt"
    output.write_text("check started\nall good\n", encoding="utf-8")
    block = sign(
        job="smoke",
        commit=head,
        result="pass",
        evidence_dir=str(evidence),
        key=str(keypair),
        repo="acme/widget",
        output_file=str(output),
    )
    block_path = tmp_path / "block.md"
    block_path.write_text(block, encoding="utf-8")
    allowed = tmp_path / "allowed_signers"
    allowed.write_text(f"operator {keypair.with_suffix('.pub').read_text().strip()}\n")
    assert run_verify(block_path, allowed, head)["verdict"] == "pass"


def test_v1_receipt_rejects_an_output_field(
    repo: Path, keypair: Path, evidence: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo)
    block, allowed, head = make_block(repo, keypair, evidence, tmp_path)
    payload, signature = extract(block.read_text())
    receipt = json.loads(payload)
    receipt["output"] = "sneaked in"
    block.write_text(compose(json.dumps(receipt, separators=(",", ":")), signature))
    _expect(block, allowed, head, "E_UNKNOWN_FIELD")
