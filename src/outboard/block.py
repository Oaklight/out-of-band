"""Extract a receipt block from text.

The grammar is byte-exact (SPEC.md §1.4). A line break is LF only; a CR stays
in the payload, so a CRLF comment fails verification instead of being silently
normalized.
"""

from __future__ import annotations

from .errors import OutboardError

MARKER = "<!-- receipt:v1 -->"
MAX_BLOCK_BYTES = 16 * 1024
JSON_FENCE = "```json"
SIG_FENCE = "```ssh-signature"
FENCE = "```"


def _invalid(code: str, message: str) -> OutboardError:
    return OutboardError(code, message, 2)


def _fence(line: str) -> str:
    return line.strip(" \t")


def extract(text: str) -> tuple[bytes, str]:
    """Return (payload bytes, signature text).

    Raises OutboardError with a SPEC.md §4.2 code and exit 2.
    """
    marker_count = text.count(MARKER)
    if marker_count == 0:
        raise _invalid("E_NO_BLOCK", "no receipt marker found")
    if marker_count > 1:
        raise _invalid("E_MULTI_BLOCK", "more than one receipt marker")

    lines = text.split("\n")
    offsets: list[int] = []
    position = 0
    for line in lines:
        offsets.append(position)
        position += len(line) + 1

    start_line = next(i for i, line in enumerate(lines) if MARKER in line)

    json_line = None
    for index in range(start_line + 1, len(lines)):
        if _fence(lines[index]) == JSON_FENCE:
            json_line = index
            break
    if json_line is None:
        raise _invalid("E_BAD_FENCE", "missing the json fence")

    close_line = None
    for index in range(json_line + 1, len(lines)):
        if _fence(lines[index]) == FENCE:
            close_line = index
            break
    if close_line is None:
        raise _invalid("E_BAD_FENCE", "unterminated json fence")

    payload_lines = lines[json_line + 1 : close_line]
    if len(payload_lines) != 1:
        raise _invalid("E_MULTI_LINE", "the json payload must be exactly one line")
    payload_text = payload_lines[0]
    if not payload_text.strip():
        raise _invalid("E_BAD_JSON", "empty json payload")

    signature_line = None
    for index in range(close_line + 1, len(lines)):
        if _fence(lines[index]) == "":
            continue
        if _fence(lines[index]) == SIG_FENCE:
            signature_line = index
        break
    if signature_line is None:
        raise _invalid("E_BAD_FENCE", "missing the ssh-signature fence")

    sig_close = None
    for index in range(signature_line + 1, len(lines)):
        if _fence(lines[index]) == FENCE:
            sig_close = index
            break
    if sig_close is None:
        raise _invalid("E_BAD_FENCE", "unterminated ssh-signature fence")

    signature_lines = lines[signature_line + 1 : sig_close]
    if not signature_lines:
        raise _invalid("E_BAD_SIGNATURE", "empty signature")

    block_end = offsets[sig_close] + len(lines[sig_close])
    block_length = len(text[offsets[start_line] : block_end].encode("utf-8"))
    if block_length > MAX_BLOCK_BYTES:
        raise _invalid("E_TOO_LARGE", f"block exceeds {MAX_BLOCK_BYTES} bytes")

    return payload_text.encode("utf-8"), "\n".join(signature_lines) + "\n"
