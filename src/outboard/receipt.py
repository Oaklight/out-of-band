"""Receipt construction, serialization, and validation.

The wire format is defined in SPEC.md §1. The signature covers the literal
bytes produced by `serialize`, never a re-encoded object.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from .errors import OutboardError

SCHEMA = "receipt/v1"
MAX_BLOCK_BYTES = 16 * 1024
MAX_CLAIMS_BYTES = 2048
MAX_CLAIM_STRING = 256
MAX_CLAIM_LIST = 16
MAX_SAFE_INT = 2**53 - 1

JOB_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CLAIM_KEY_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TOOL_RE = re.compile(r"^outboard/\d+\.\d+\.\d+$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

FIELDS = (
    "schema",
    "repo",
    "commit",
    "tree",
    "job",
    "result",
    "issued_at",
    "tool",
    "evidence",
    "claims",
)


def build(
    *,
    repo: str,
    commit: str,
    tree: str,
    job: str,
    result: str,
    issued_at: str,
    tool: str,
    count: int,
    digest: str,
    claims: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "repo": repo,
        "commit": commit,
        "tree": tree,
        "job": job,
        "result": result,
        "issued_at": issued_at,
        "tool": tool,
        "evidence": {"count": count, "digest": digest},
        "claims": claims or {},
    }
    return receipt


def serialize(receipt: dict[str, Any]) -> bytes:
    """Compact JSON on one line, UTF-8. No trailing newline."""
    return json.dumps(receipt, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compose_block(payload: bytes, signature: str) -> str:
    return (
        "<!-- receipt:v1 -->\n"
        "```json\n"
        f"{payload.decode('utf-8')}\n"
        "```\n"
        "```ssh-signature\n"
        f"{signature.strip()}\n"
        "```\n"
    )


def _bad(code: str, message: str) -> OutboardError:
    return OutboardError(code, message, 2)


def _is_int(value: Any) -> bool:
    return type(value) is int


def _validate_claim_value(key: str, value: Any) -> None:
    def check_scalar(item: Any) -> None:
        if isinstance(item, str):
            if len(item.encode("utf-8")) > MAX_CLAIM_STRING:
                raise _bad(
                    "E_CLAIMS_LIMIT", f"claim {key!r} string exceeds {MAX_CLAIM_STRING} bytes"
                )
            if any(ord(ch) < 32 or ord(ch) == 127 for ch in item):
                raise _bad("E_CLAIMS_LIMIT", f"claim {key!r} contains a control character")
        elif isinstance(item, bool):
            return
        elif _is_int(item):
            if abs(item) > MAX_SAFE_INT:
                raise _bad("E_CLAIMS_LIMIT", f"claim {key!r} integer is out of range")
        else:
            raise _bad("E_BAD_TYPE", f"claim {key!r} has a disallowed type")

    if isinstance(value, list):
        if len(value) > MAX_CLAIM_LIST:
            raise _bad("E_CLAIMS_LIMIT", f"claim {key!r} list exceeds {MAX_CLAIM_LIST} items")
        for item in value:
            check_scalar(item)
    else:
        check_scalar(value)


def validate(receipt: Any) -> None:
    """Validate a receipt object against SPEC.md §1.2."""
    if not isinstance(receipt, dict):
        raise _bad("E_BAD_JSON", "receipt must be a JSON object")

    unknown = set(receipt) - set(FIELDS)
    if unknown:
        raise _bad("E_UNKNOWN_FIELD", f"unknown field(s): {', '.join(sorted(unknown))}")
    missing = set(FIELDS) - set(receipt)
    if missing:
        raise _bad("E_BAD_TYPE", f"missing field(s): {', '.join(sorted(missing))}")

    if receipt["schema"] != SCHEMA:
        raise _bad("E_BAD_SCHEMA", f"schema must be {SCHEMA!r}")
    for name in ("repo", "commit", "tree", "job", "result", "issued_at", "tool"):
        if not isinstance(receipt[name], str):
            raise _bad("E_BAD_TYPE", f"{name} must be a string")

    if not REPO_RE.match(receipt["repo"]):
        raise _bad("E_BAD_VALUE", "repo must be owner/name")
    if not SHA_RE.match(receipt["commit"]):
        raise _bad("E_BAD_VALUE", "commit must be 40 lowercase hex")
    if not SHA_RE.match(receipt["tree"]):
        raise _bad("E_BAD_VALUE", "tree must be 40 lowercase hex")
    if not JOB_RE.match(receipt["job"]):
        raise _bad("E_BAD_VALUE", "job has a disallowed character or length")
    if receipt["result"] not in ("pass", "fail"):
        raise _bad("E_BAD_VALUE", "result must be pass or fail")
    if not TIMESTAMP_RE.match(receipt["issued_at"]):
        raise _bad("E_BAD_VALUE", "issued_at must be YYYY-MM-DDTHH:MM:SSZ")
    try:
        datetime.strptime(receipt["issued_at"], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise _bad("E_BAD_VALUE", "issued_at is not a real timestamp") from exc
    if not TOOL_RE.match(receipt["tool"]):
        raise _bad("E_BAD_VALUE", "tool must be outboard/<semver>")

    evidence = receipt["evidence"]
    if not isinstance(evidence, dict):
        raise _bad("E_BAD_TYPE", "evidence must be an object")
    if set(evidence) != {"count", "digest"}:
        raise _bad("E_UNKNOWN_FIELD", "evidence must contain exactly count and digest")
    count = evidence["count"]
    if not _is_int(count) or count < 0 or count > 1_000_000:
        raise _bad("E_BAD_VALUE", "evidence.count must be an integer in 0..1000000")
    if not isinstance(evidence["digest"], str) or not DIGEST_RE.match(evidence["digest"]):
        raise _bad("E_BAD_VALUE", "evidence.digest must be sha256:<64 hex>")

    claims = receipt["claims"]
    if not isinstance(claims, dict):
        raise _bad("E_BAD_TYPE", "claims must be an object")
    for key, value in claims.items():
        if not CLAIM_KEY_RE.match(key):
            raise _bad("E_BAD_VALUE", f"claim key is invalid: {key!r}")
        _validate_claim_value(key, value)
    if (
        len(json.dumps(claims, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        > MAX_CLAIMS_BYTES
    ):
        raise _bad("E_CLAIMS_LIMIT", f"claims exceed {MAX_CLAIMS_BYTES} bytes")
