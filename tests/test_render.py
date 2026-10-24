from __future__ import annotations

from oob.block import extract
from oob.render import render

PAYLOAD = (
    '{"schema":"receipt/v2","repo":"acme/widget","commit":"'
    + "a" * 40
    + '","tree":"'
    + "b" * 40
    + '","job":"smoke","result":"pass","issued_at":"2026-10-24T00:00:00Z",'
    '"tool":"oob/0.5.0","evidence":{"count":1,"digest":"sha256:'
    + "c"
    * 64
    + '"},"claims":{"device_count":2,"note":"a|b <script>x</script>"},'
    '"output":"line one\\nline two"}'
)
BLOCK = (
    f"<!-- receipt:v1 -->\n```json\n{PAYLOAD}\n```\n"
    "```ssh-signature\n-----BEGIN SSH SIGNATURE-----\nAAAA\n"
    "-----END SSH SIGNATURE-----\n```\n"
)


def test_render_keeps_the_exact_payload_and_signature() -> None:
    rendered = render(BLOCK)
    payload, signature = extract(rendered)
    assert payload.decode("utf-8") == PAYLOAD
    assert "BEGIN SSH SIGNATURE" in signature


def test_render_shows_a_table_and_folds_the_block() -> None:
    rendered = render(BLOCK)
    assert "| job | smoke |" in rendered
    assert "| evidence | 1 files, sha256:" in rendered
    assert "<details><summary>Signed block</summary>" in rendered
    assert "<details><summary>Check output</summary>" in rendered


def test_render_escapes_claims_and_output() -> None:
    rendered = render(BLOCK)
    assert "&#124;" in rendered
    assert "&lt;script&gt;" in rendered
    assert "line one\nline two" in rendered
