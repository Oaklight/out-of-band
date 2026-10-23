"""Parse --claims k=v pairs into the claims object."""

from __future__ import annotations

import json
from typing import Any

from .errors import OutboardError
from .receipt import CLAIM_KEY_RE


def _usage(message: str) -> OutboardError:
    return OutboardError("E_USAGE", message)


def parse_value(raw: str) -> Any:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if parsed is None or isinstance(parsed, float):
        raise _usage(f"claim value is not allowed: {raw!r}")
    if isinstance(parsed, dict):
        raise _usage(f"claim value must be a scalar or a list of scalars: {raw!r}")
    if isinstance(parsed, list):
        for item in parsed:
            if item is None or isinstance(item, (float, dict, list)):
                raise _usage(f"claim list contains a disallowed value: {raw!r}")
        return parsed
    return parsed


def parse_pairs(pairs: list[str]) -> dict[str, Any]:
    claims: dict[str, Any] = {}
    for pair in pairs:
        key, separator, raw = pair.partition("=")
        if not separator or not key:
            raise _usage(f"--claims expects k=v, got {pair!r}")
        if not CLAIM_KEY_RE.match(key):
            raise _usage(f"claim key is invalid: {key!r}")
        if key in claims:
            raise _usage(f"claim key repeated: {key!r}")
        claims[key] = parse_value(raw)
    return claims
