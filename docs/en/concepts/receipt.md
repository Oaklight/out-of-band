# Receipts

[English](receipt.md) | [中文](../../zh/concepts/receipt.md)

A receipt is one statement, signed by one key, about one commit. It travels as
a pull request comment, a dispatch input, or a file. Everything else in the
project exists to produce, check, or display it.

## The block

````text
<!-- receipt:v1 -->
```json
{"schema":"receipt/v2","repo":"acme/widget","commit":"6e5b8a4...","tree":"0d3c1f...","job":"smoke","result":"pass","issued_at":"2026-10-24T19:30:00Z","tool":"oob/0.5.0","evidence":{"count":2,"digest":"sha256:0ac06086..."},"output":"2 passed in 41s","claims":{"device":"v100"}}
```
```ssh-signature
-----BEGIN SSH SIGNATURE-----
...
-----END SSH SIGNATURE-----
```
````

Three parts:

- the marker `<!-- receipt:v1 -->`, so a workflow can find the block in a
  comment;
- exactly one line of JSON;
- one SSH signature over the literal bytes of that line.

The signature covers the line as written: no re-serialization, no whitespace
normalization, no line-ending conversion. Change one byte and verification
fails. Text outside the block is ignored.

## What the JSON binds

| Field | What it says |
| --- | --- |
| `repo` | the repository, `owner/name` |
| `commit` | the full commit SHA that was tested |
| `tree` | the tree of that commit, so a rewritten commit cannot reuse the receipt |
| `job` | the name of the job, agreed with the consumer |
| `result` | `pass` or `fail` |
| `evidence.digest` | `sha256:` over the evidence manifest |
| `evidence.count` | how many files the manifest lists |
| `issued_at` | when the operator says it was signed, in UTC |
| `tool` | which version produced it; informational, never trusted |
| `output` | optional, up to 4 KiB of curated check output (schema v2) |
| `claims` | optional public facts, up to 2048 bytes |

`repo`, `commit`, `tree`, and `job` are checked against values from the caller's
context, never against other fields in the receipt. Before the signature
verifies, those values are attacker-controlled.

## Schema versions

- `receipt/v1` has no `output`.
- `receipt/v2` adds `output` and changes nothing else.
- `oob sign` emits v2 only when `--output-file` is given.
- A v2 verifier reads both. A v1 verifier reads only v1.

The schema string, not the package version, is the compatibility boundary.

## Claims

Claims are small facts the consumer may want to display or use later: a device
name, a batch id, a model hash, a link to an evidence archive.

- Keys match `[a-z][a-z0-9_.-]{0,63}`.
- Values are strings, integers within the safe JSON range, booleans, or arrays
  of at most 16 of those.
- No nested objects, no floats, no null.
- The serialized object is at most 2048 bytes.

Claims are data. They are shown in the check summary inside a fenced code
block, with Markdown and mention syntax escaped, so a claim cannot become a
link or ping someone.

`claims.evidence_url` is special: when the verifier has no `evidence-url` or
`evidence-file`, it fetches this URL. That lets a receipt carry its own
evidence location. The URL must be `https`.

## Limits

| Limit | Value |
| --- | --- |
| Whole block | 16 KiB |
| JSON line | one line, no line breaks |
| `output` | 4096 bytes |
| `claims` | 2048 bytes serialized |
| Evidence files | 1000 |
| Evidence bytes | 50 MiB |

The verifier applies the size limit before parsing, so a hostile comment cannot
make it do much work.

## What a receipt does not say

It does not say the job ran, that the result is correct, or that the machine
was uncompromised. It says the holder of a listed key signed these bytes. See
[Trust](trust.md) for the full boundary.

The normative grammar, extraction rules, and field ranges are in
[SPEC.md](../../../SPEC.md).
