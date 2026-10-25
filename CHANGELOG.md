# Changelog

Notable changes, newest first. The format follows Keep a Changelog; this
project uses semantic versions for the package and a separate schema version
for receipts.

## 0.5.0 - 2026-10-25

### Added

- Composite action in `action.yml`, so the verifier can run as a step. The
  reusable workflow remains available.
- `oob render`, which turns a receipt block into a readable Markdown comment
  while preserving the signed bytes.
- `evidence-file` input, alongside `evidence-url` and the signed
  `claims.evidence_url`.
- Evidence is required by default. `require-evidence: false` restores
  digest-only runs.
- Evidence manifest and bounded text previews in the job summary; the extracted
  archive is uploaded as the `oob-evidence` artifact.
- `report` input. `false` computes the verdict without publishing a check or
  comment, for tests and dry runs.
- Six complete examples under `examples/`, with an index.
- `SECURITY.md`, `CONTRIBUTING.md`, and this changelog.

### Changed

- `unverified` publishes the `failure` conclusion. The state and error code
  remain in the check title and summary.
- The trust root, receipt collection, and evidence rules are documented as four
  states: `verified`, `failed`, `unverified`, `not applicable`.
- Documentation is grouped by concepts, reference, and guides. English and
  Chinese trees mirror each other.

### Fixed

- Passing an evidence file whose name was already `evidence.tgz` copied it onto
  itself and produced an empty archive.
- An evidence manifest written from a composite action step could disappear
  because the runner keeps only the last step summary. It is now written in the
  publish step.
- The action's default `version` now matches the release.

## 0.4.1 - 2026-10-24

### Added

- Python 3.10 support, and CI on 3.10 through 3.14.

## 0.4.0 - 2026-10-24

### Changed

- Renamed the project from `outboard` to `out-of-band`; the CLI is `oob`. The
  `outboard` distribution is retired.
- The verifier checks out the caller's default branch explicitly, and the
  receipt is selected by commit and job.

## 0.3.0 - 2026-10-24

### Added

- Optional evidence upload. The archive is hashed and compared with the signed
  digest before it is kept.
- Single-file `oob.pyz` build for hosts without PyPI access.

## 0.2.0 - 2026-10-24

### Added

- Schema `receipt/v2`, carrying up to 4 KiB of curated check output.
- Receipts are ignored when they name a different commit.

## 0.1.0 - 2026-10-23

First release: sign a receipt for a commit, verify it against
`allowed_signers`, and publish a check run from a reusable workflow.
