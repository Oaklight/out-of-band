from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")
    git(root, "remote", "add", "origin", "git@github.com:acme/widget.git")
    (root / "a.txt").write_text("hello\n", encoding="utf-8")
    git(root, "add", "a.txt")
    git(root, "commit", "-m", "init")
    return root


@pytest.fixture
def keypair(tmp_path: Path) -> Path:
    key = tmp_path / "key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
        check=True,
    )
    return key


@pytest.fixture
def evidence(tmp_path: Path) -> Path:
    directory = tmp_path / "evidence"
    (directory / "nested").mkdir(parents=True)
    (directory / "run.log").write_text("ok\n", encoding="utf-8")
    (directory / "nested" / "result.json").write_text('{"passed":true}\n', encoding="utf-8")
    return directory


@pytest.fixture
def head(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD")
