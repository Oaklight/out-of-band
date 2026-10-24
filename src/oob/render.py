"""Render a signed receipt block as a Markdown comment."""

from __future__ import annotations

import html
import json
from typing import Any

from .block import MARKER, extract
from .errors import OutboardError


def _cell(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = html.escape(text, quote=False)
    return text.replace("|", "&#124;").replace("\n", " ")


def _row(name: str, value: Any) -> str:
    return f"| {name} | {_cell(value)} |"


def render(block_text: str) -> str:
    """Return a Markdown comment that still contains the exact signed block.

    The table is presentation only. A verifier reads the fenced block and
    ignores everything around it, so an edited table cannot change a verdict.
    """
    payload, signature = extract(block_text)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise OutboardError("E_BAD_JSON", "receipt payload is not valid JSON") from exc
    if not isinstance(data, dict):
        raise OutboardError("E_BAD_JSON", "receipt payload is not an object")

    lines = [MARKER, "", "| field | value |", "| --- | --- |"]
    for name in ("repo", "commit", "tree", "job", "result", "issued_at", "tool"):
        if name in data:
            lines.append(_row(name, data[name]))

    evidence = data.get("evidence")
    if isinstance(evidence, dict):
        count = evidence.get("count")
        digest = evidence.get("digest")
        lines.append(_row("evidence", f"{count} files, {digest}"))

    claims = data.get("claims")
    if isinstance(claims, dict) and claims:
        lines += ["", "| claim | value |", "| --- | --- |"]
        for key in sorted(claims):
            lines.append(_row(key, claims[key]))

    output = data.get("output")
    if isinstance(output, str) and output.strip():
        lines += [
            "",
            "<details><summary>Check output</summary>",
            "",
            f"<pre>{html.escape(output)}</pre>",
            "",
            "</details>",
        ]

    lines += [
        "",
        "<details><summary>Signed block</summary>",
        "",
        "```json",
        payload.decode("utf-8"),
        "```",
        "```ssh-signature",
        signature.rstrip("\n"),
        "```",
        "</details>",
        "",
    ]
    return "\n".join(lines)
