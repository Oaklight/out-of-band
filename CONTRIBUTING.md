# Contributing

## Set up

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

Python 3.10 through 3.14 are supported. CI runs the test suite on all five.

## What lives where

| Path | Contents |
| --- | --- |
| `src/oob/` | CLI, signing, verification, rendering, evidence, workflow helpers |
| `tests/` | unit and workflow-helper tests |
| `action.yml` | composite action |
| `.github/workflows/verify.yml` | reusable verifier |
| `.github/workflows/selftest.yml` | end-to-end self-test |
| `docs/en`, `docs/zh` | documentation, one tree per language |
| `site/` | GitHub Pages tour |
| `SPEC.md` | normative format and contract |

## Self-test

`selftest.yml` signs real receipts and asserts both positive and negative
outcomes. It runs on every pull request that touches the action, the workflow,
the CLI, or the self-test itself. Negative cases use `report: false`, so they
assert a verdict without publishing a failing check.

When you change a check name, update branch protection in the same change; the
string is the protected API.

## Documentation

- English and Chinese trees must stay structurally in sync: same files, same
  heading order, same code blocks.
- Keep commands, field names, input names, and links unchanged when translating.
- Links between languages use the other tree; links inside a tree stay relative.
- Prefer concrete statements over marketing. Explain what the code does, what it
  does not do, and what the reader must supply.
- If a change alters behavior, update the page that documents that behavior,
  `README_en.md`, `README_zh.md` when the summary changed, and `CHANGELOG.md`.

## Schema changes

`SPEC.md` is normative. Adding or removing a receipt field, or changing a
meaning, needs a new schema version and a section in the spec. A verifier keeps
accepting older schemas for the supported lines.

## Pull requests

- Keep one topic per pull request. Docs, behavior, and release chores are
  separate unless they are the same change.
- Add a test for behavior changes. For a fix, include the failing case first.
- Add a `CHANGELOG.md` entry for anything a user can observe.
- Use a conventional prefix in the commit subject: `feat:`, `fix:`, `docs:`,
  `test:`, `ci:`, `chore:`, `change:`.
- Pin actions in examples by full SHA with a version comment.

By contributing you agree that your contribution is licensed under
Apache-2.0.
