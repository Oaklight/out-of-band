"""Thin, local-only git queries. No network."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .errors import OutboardError

REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def repo_root(cwd: Path | None = None) -> Path:
    proc = _run(["rev-parse", "--show-toplevel"], cwd)
    if proc.returncode != 0:
        raise OutboardError("E_NOT_A_REPO", "not inside a git repository")
    return Path(proc.stdout.strip())


def parse_repo_url(url: str) -> str:
    """Turn an SSH or HTTPS remote into owner/name."""
    value = url.strip()
    value = value.removesuffix(".git")
    if "://" in value:
        _, _, rest = value.partition("://")
        _, _, path = rest.partition("/")
        value = path
    elif ":" in value and not value.startswith("/"):
        _, _, path = value.partition(":")
        value = path
    value = value.strip("/")
    if value.count("/") != 1 or not REPO_RE.match(value):
        raise OutboardError("E_NO_REMOTE", f"cannot derive owner/name from remote: {url!r}")
    return value


def origin_repo(cwd: Path | None = None) -> str:
    proc = _run(["remote", "get-url", "origin"], cwd)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise OutboardError("E_NO_REMOTE", "no origin remote; pass --repo")
    return parse_repo_url(proc.stdout.strip())


def assert_commit(sha: str, cwd: Path | None = None) -> None:
    if not SHA_RE.match(sha):
        raise OutboardError("E_USAGE", "--commit must be a full 40-hex SHA")
    proc = _run(["cat-file", "-e", f"{sha}^{{commit}}"], cwd)
    if proc.returncode != 0:
        raise OutboardError("E_UNKNOWN_COMMIT", f"commit not found locally: {sha}")


def commit_tree(sha: str, cwd: Path | None = None) -> str:
    proc = _run(["rev-parse", f"{sha}^{{tree}}"], cwd)
    if proc.returncode != 0:
        raise OutboardError("E_UNKNOWN_COMMIT", f"cannot read tree of commit: {sha}")
    return proc.stdout.strip()


def is_dirty(cwd: Path | None = None) -> bool:
    proc = _run(["status", "--porcelain"], cwd)
    if proc.returncode != 0:
        raise OutboardError("E_NOT_A_REPO", "cannot read git status")
    return bool(proc.stdout.strip())
