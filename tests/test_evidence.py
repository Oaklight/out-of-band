from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from oob.errors import OutboardError
from oob.evidence import digest_directory


def test_manifest_is_sorted_and_stable(tmp_path: Path, keypair: Path) -> None:
    directory = tmp_path / "ev"
    (directory / "b").mkdir(parents=True)
    (directory / "b" / "z.txt").write_bytes(b"z")
    (directory / "a.txt").write_bytes(b"a")

    count, digest = digest_directory(directory, keypair)
    assert count == 2

    expected = (
        hashlib.sha256(b"a").hexdigest().encode()
        + b"  a.txt\n"
        + hashlib.sha256(b"z").hexdigest().encode()
        + b"  b/z.txt\n"
    )
    assert digest == "sha256:" + hashlib.sha256(expected).hexdigest()
    assert digest_directory(directory, keypair) == (count, digest)


def test_empty_directory(tmp_path: Path, keypair: Path) -> None:
    directory = tmp_path / "empty"
    directory.mkdir()
    count, digest = digest_directory(directory, keypair)
    assert count == 0
    assert digest == "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_symlink_is_rejected(tmp_path: Path, keypair: Path) -> None:
    directory = tmp_path / "ev"
    directory.mkdir()
    (directory / "real.txt").write_text("x", encoding="utf-8")
    (directory / "link.txt").symlink_to(directory / "real.txt")
    with pytest.raises(OutboardError) as caught:
        digest_directory(directory, keypair)
    assert caught.value.code == "E_EVIDENCE_TYPE"


def test_newline_in_filename_is_rejected(tmp_path: Path, keypair: Path) -> None:
    directory = tmp_path / "ev"
    directory.mkdir()
    (directory / "bad\nname").write_text("x", encoding="utf-8")
    with pytest.raises(OutboardError) as caught:
        digest_directory(directory, keypair)
    assert caught.value.code == "E_EVIDENCE_PATH"
