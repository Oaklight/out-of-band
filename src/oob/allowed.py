"""Parse an allowed_signers file.

Only plain keys with plain principals are supported in v0.1. Key options are
rejected rather than ignored, so a validity window can never be silently
bypassed.
"""

from __future__ import annotations

from pathlib import Path

from .errors import OutboardError

WILDCARDS = ("*", "?", "!")
KEY_PREFIXES = ("ssh-", "ecdsa-", "sk-ssh-", "sk-ecdsa-")


def _bad(message: str) -> OutboardError:
    return OutboardError("E_BAD_ALLOWED_SIGNERS", message, 3)


def parse(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise _bad(f"cannot read allowed_signers: {path}") from exc

    principals: list[str] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 3:
            raise _bad(f"line {number}: expected principal, key type, and key")
        names = fields[0]
        key_type = fields[1]
        if not key_type.startswith(KEY_PREFIXES):
            raise _bad(f"line {number}: key options are not supported in v0.1")
        for name in names.split(","):
            if not name or any(char in name for char in WILDCARDS):
                raise _bad(f"line {number}: wildcard principal is not allowed")
            principals.append(name)

    if not principals:
        raise _bad("no keys in allowed_signers")
    return principals
