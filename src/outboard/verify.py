"""The verify command: strict parse, signature, bindings."""

from __future__ import annotations

import base64
import binascii
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from . import allowed
from .block import extract
from .errors import OutboardError
from .receipt import validate

ARMOR_BEGIN = "-----BEGIN SSH SIGNATURE-----"
ARMOR_END = "-----END SSH SIGNATURE-----"


def _invalid(code: str, message: str) -> OutboardError:
    return OutboardError(code, message, 2)


def _parse_json(payload: bytes) -> dict[str, Any]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _invalid("E_BAD_JSON", "payload is not valid UTF-8") from exc

    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _invalid("E_DUP_KEY", f"duplicate key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise _invalid("E_BAD_JSON", f"non-finite number: {value}")

    try:
        parsed = json.loads(
            text,
            object_pairs_hook=no_duplicates,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise _invalid("E_BAD_JSON", "payload is not JSON") from exc
    return parsed


def _check_armor(signature: str) -> None:
    lines = signature.strip().splitlines()
    if len(lines) < 3 or lines[0] != ARMOR_BEGIN or lines[-1] != ARMOR_END:
        raise _invalid("E_BAD_SIGNATURE", "signature armor is malformed")
    try:
        base64.b64decode("".join(lines[1:-1]), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise _invalid("E_BAD_SIGNATURE", "signature body is not base64") from exc


def _verify_signature(payload: bytes, signature: str, allowed_path: Path) -> str:
    principals = allowed.parse(allowed_path)
    _check_armor(signature)
    with tempfile.TemporaryDirectory(prefix="outboard-") as tmp:
        signature_file = Path(tmp) / "block.sig"
        signature_file.write_text(signature, encoding="utf-8")
        for principal in principals:
            proc = subprocess.run(
                [
                    "ssh-keygen",
                    "-Y",
                    "verify",
                    "-f",
                    str(allowed_path),
                    "-I",
                    principal,
                    "-n",
                    "receipt",
                    "-s",
                    str(signature_file),
                ],
                input=payload,
                capture_output=True,
                check=False,
            )
            if proc.returncode == 0:
                return principal
    raise _invalid("E_NO_PRINCIPAL", "no allowed principal accepts the signature")


def _bind(receipt: dict[str, Any], repo: str, commit: str, job: str, tree: str | None) -> None:
    if receipt["repo"].lower() != repo.lower():
        raise _invalid("E_WRONG_REPO", f"expected {repo!r}, got {receipt['repo']!r}")
    if receipt["commit"].lower() != commit.lower():
        raise _invalid("E_WRONG_COMMIT", f"expected {commit}, got {receipt['commit']}")
    if tree is not None and receipt["tree"].lower() != tree.lower():
        raise _invalid("E_WRONG_TREE", f"expected {tree}, got {receipt['tree']}")
    if receipt["job"] != job:
        raise _invalid("E_WRONG_JOB", f"expected {job!r}, got {receipt['job']!r}")


def verify(
    *,
    block_path: str,
    allowed_signers: str,
    repo: str,
    commit: str,
    job: str,
    tree: str | None = None,
) -> dict[str, Any]:
    path = Path(block_path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise OutboardError("E_USAGE", f"cannot read block: {path}") from exc
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _invalid("E_BAD_JSON", "block is not valid UTF-8") from exc

    payload, signature = extract(text)
    receipt = _parse_json(payload)
    validate(receipt)
    _verify_signature(payload, signature, Path(allowed_signers))
    _bind(receipt, repo, commit, job, tree)

    return {
        "verdict": receipt["result"],
        "code": "OK",
        "repo": receipt["repo"],
        "commit": receipt["commit"],
        "job": receipt["job"],
    }
