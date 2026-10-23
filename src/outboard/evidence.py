"""Evidence directory digest.

The manifest is one line per regular file, sorted by the UTF-8 bytes of the
relative path, then hashed. See SPEC.md §2.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from .errors import OutboardError

CHUNK = 1 << 20


def _path_error(message: str) -> OutboardError:
    return OutboardError("E_EVIDENCE_PATH", message)


def _relative_path(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    try:
        rel.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise _path_error(f"filename is not valid UTF-8: {rel!r}") from exc
    if "\n" in rel or "\r" in rel or "\x00" in rel:
        raise _path_error(f"filename contains a forbidden character: {rel!r}")
    return rel


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest_directory(
    directory: str | os.PathLike[str],
    key_path: str | os.PathLike[str],
) -> tuple[int, str]:
    """Return (count, digest) for an evidence directory.

    The key containment check runs before the walk so the key itself can never
    enter the digest.
    """
    root = Path(directory)
    key = Path(key_path)

    if not root.exists():
        raise OutboardError("E_EVIDENCE_READ", f"evidence directory does not exist: {directory}")
    if not root.is_dir():
        raise OutboardError("E_EVIDENCE_READ", f"evidence path is not a directory: {directory}")
    if root.is_symlink():
        raise OutboardError("E_EVIDENCE_TYPE", f"evidence directory is a symlink: {directory}")

    real_root = root.resolve()
    real_key = key.resolve()
    if real_key == real_root or real_root in real_key.parents:
        raise OutboardError(
            "E_KEY_IN_EVIDENCE",
            "the signing key is inside the evidence directory",
        )

    entries: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(real_root, followlinks=False):
        base = Path(dirpath)
        for name in dirnames:
            if (base / name).is_symlink():
                raise OutboardError("E_EVIDENCE_TYPE", f"symlink in evidence directory: {name}")
        for name in filenames:
            candidate = base / name
            if candidate.is_symlink():
                raise OutboardError("E_EVIDENCE_TYPE", f"symlink in evidence directory: {name}")
            if not candidate.is_file():
                raise OutboardError(
                    "E_EVIDENCE_TYPE",
                    f"non-regular file in evidence directory: {name}",
                )
            entries.append((_relative_path(candidate, real_root), _sha256_file(candidate)))

    entries.sort(key=lambda item: item[0].encode("utf-8"))
    manifest = b"".join(f"{file_digest}  {rel}\n".encode() for rel, file_digest in entries)
    return len(entries), "sha256:" + hashlib.sha256(manifest).hexdigest()
