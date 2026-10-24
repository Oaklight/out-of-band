"""The sign command: bind a result to a commit and sign the bytes."""

from __future__ import annotations

import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from . import __version__, gitops
from .claims import parse_pairs
from .errors import OutboardError
from .evidence import digest_directory
from .receipt import MAX_OUTPUT_BYTES, build, compose_block, serialize, validate


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ssh_sign(payload: bytes, key: Path) -> str:
    if not key.is_file():
        raise OutboardError("E_USAGE", f"signing key not found: {key}")
    with tempfile.TemporaryDirectory(prefix="oob-") as tmp:
        data = Path(tmp) / "receipt.json"
        data.write_bytes(payload)
        proc = subprocess.run(
            ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "receipt", str(data)],
            capture_output=True,
            check=False,
        )
        signature = Path(f"{data}.sig")
        if proc.returncode != 0 or not signature.exists():
            detail = proc.stderr.decode("utf-8", errors="replace").strip()
            raise OutboardError("E_SIGN_FAILED", detail or "ssh-keygen could not sign")
        return signature.read_text(encoding="utf-8")


def _read_output(path: str) -> str | None:
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise OutboardError("E_USAGE", f"cannot read output file: {path}") from exc
    if len(data) > MAX_OUTPUT_BYTES:
        raise OutboardError("E_OUTPUT_LIMIT", f"output exceeds {MAX_OUTPUT_BYTES} bytes")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OutboardError("E_USAGE", "output is not valid UTF-8") from exc
    return text if text.strip() else None


def sign(
    *,
    job: str,
    commit: str,
    result: str,
    evidence_dir: str,
    key: str,
    repo: str | None = None,
    claims: list[str] | None = None,
    allow_dirty: bool = False,
    output_file: str | None = None,
) -> str:
    gitops.repo_root()  # fail early outside a repository
    resolved_repo = repo or gitops.origin_repo()
    commit = commit.lower()
    gitops.assert_commit(commit)
    tree = gitops.commit_tree(commit)
    if not allow_dirty and gitops.is_dirty():
        raise OutboardError(
            "E_DIRTY_WORKTREE",
            "worktree has uncommitted changes; commit first or pass --allow-dirty",
        )

    count, digest = digest_directory(evidence_dir, key)
    receipt = build(
        repo=resolved_repo,
        commit=commit,
        tree=tree,
        job=job,
        result=result,
        issued_at=_now(),
        tool=f"oob/{__version__}",
        count=count,
        digest=digest,
        claims=parse_pairs(claims or []),
        output=_read_output(output_file) if output_file else None,
    )
    validate(receipt)
    payload = serialize(receipt)
    signature = _ssh_sign(payload, Path(key))
    return compose_block(payload, signature)
