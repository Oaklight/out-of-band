"""Helpers used by the reusable workflow.

Two entry points, invoked as `python -m oob.workflow collect|publish`.
They are not part of the public CLI: creating a check run requires the Actions
App identity, so publishing stays in the workflow (SPEC.md §5.3).
"""

from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

from .block import MARKER, extract
from .errors import EXIT_ERROR, OutboardError
from .evidence import digest_directory

MAX_COMMENTS = 5000
MAX_EVIDENCE_BYTES = 50 * 1024 * 1024
MAX_EVIDENCE_FILES = 1000
# Installation tokens cannot call GET /user; in Actions the comment author is
# always the Actions app bot.
BOT_LOGIN = "github-actions[bot]"
STATE_MARKER = "<!-- oob:state -->"


def _set_output(**values: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.writelines(f"{key}={value}\n" for key, value in values.items())


def _gh(*args: str, stdin: str | None = None) -> str:
    proc = subprocess.run(
        ["gh", *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise OutboardError("E_INTERNAL", proc.stderr.strip() or "gh failed")
    return proc.stdout


def _comments(repo: str, pr: str) -> list[dict[str, Any]]:
    raw = _gh(
        "api",
        "--paginate",
        "--slurp",
        f"repos/{repo}/issues/{pr}/comments?per_page=100",
    )
    pages = json.loads(raw)
    comments = [item for page in pages for item in page]
    if len(comments) > MAX_COMMENTS:
        raise OutboardError(
            "E_TOO_MANY_COMMENTS",
            f"more than {MAX_COMMENTS} comments to scan",
        )
    return comments


def _is_trusted(comment: dict[str, Any], trusted: list[str]) -> bool:
    login = (comment.get("user") or {}).get("login", "")
    if trusted:
        return login.lower() in trusted
    return comment.get("author_association") in {"OWNER", "MEMBER", "COLLABORATOR"}


def _job_of(payload: bytes) -> str | None:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    job = value.get("job")
    return job if isinstance(job, str) else None


def _commit_of(payload: bytes) -> str | None:
    """The commit a block claims, read without trusting it.

    This narrows the candidate set before signature verification. A forged
    claim can hide a block from itself; it cannot authenticate one.
    """
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    commit = value.get("commit")
    return commit.lower() if isinstance(commit, str) else None


def collect() -> int:
    temp = Path(os.environ["RUNNER_TEMP"])
    receipt = (os.environ.get("RECEIPT") or "").strip()
    pr = (os.environ.get("PR") or "0").strip()
    repo = os.environ["GITHUB_REPOSITORY"]
    trusted = [
        name.strip().lower()
        for name in (os.environ.get("TRUSTED") or "").split(",")
        if name.strip()
    ]

    if receipt:
        (temp / "receipt.md").write_text(receipt, encoding="utf-8")
        _set_output(found="true", code="", source="input")
        return 0

    if not pr.isdigit() or int(pr) <= 0:
        _set_output(found="false", code="", source="none")
        return 0

    comments = _comments(repo, pr)
    bodies = [
        comment.get("body") or ""
        for comment in comments
        if MARKER in (comment.get("body") or "") and _is_trusted(comment, trusted)
    ]
    if not bodies:
        _set_output(found="false", code="", source="comments")
        return 0

    expected = (os.environ.get("COMMIT") or "").strip().lower()
    if not expected:
        # No commit to filter on. Keep the previous behaviour for callers that
        # invoke collect() directly: a single body is passed through and the
        # verifier decides.
        if len(bodies) > 1:
            seen = set()
            for body in bodies:
                try:
                    payload, signature = extract(body)
                except OutboardError:
                    _set_output(found="false", code="E_MULTI_BLOCK", source="comments")
                    return 0
                seen.add((payload, signature))
            if len(seen) > 1:
                _set_output(found="false", code="E_MULTI_BLOCK", source="comments")
                return 0
        (temp / "receipt.md").write_text(bodies[0], encoding="utf-8")
        _set_output(found="true", code="", source="comments")
        return 0

    parsed: list[tuple[bytes, str, str]] = []
    first_error: OutboardError | None = None
    for body in bodies:
        try:
            payload, signature = extract(body)
        except OutboardError as exc:
            first_error = first_error or exc
            continue
        parsed.append((payload, signature, body))

    blocks = [block for block in parsed if _commit_of(block[0]) == expected]
    if not blocks:
        # Trusted markers with nothing parseable at all are malformed, not
        # evidence about another commit; report the parse error so the author
        # can fix the block. Otherwise every block names some other commit.
        code = first_error.code if not parsed and first_error is not None else "E_WRONG_COMMIT"
        _set_output(found="false", code=code, source="comments")
        return 0

    # Several jobs can attest the same commit; a job only ever considers its
    # own block, so one job's receipt cannot collide with another's.
    expected_job = os.environ.get("JOB") or ""
    if expected_job:
        matching = [block for block in blocks if _job_of(block[0]) == expected_job]
        if not matching:
            _set_output(found="false", code="E_WRONG_JOB", source="comments")
            return 0
        blocks = matching

    if len({(payload, signature) for payload, signature, _ in blocks}) > 1:
        _set_output(found="false", code="E_MULTI_BLOCK", source="comments")
        return 0

    (temp / "receipt.md").write_text(blocks[0][2], encoding="utf-8")
    _set_output(found="true", code="", source="comments")
    return 0


def _receipt_display(receipt_path: Path) -> tuple[str, str]:
    """Return (claims block, output details), both empty when absent.

    Called only after verification. Claims use an indented code block; the
    output uses <pre> so a transcript cannot inject Markdown or mentions.
    """
    try:
        payload, _ = extract(receipt_path.read_text(encoding="utf-8"))
        data = json.loads(payload)
    except (OSError, OutboardError, json.JSONDecodeError):
        return "", ""
    if not isinstance(data, dict):
        return "", ""

    claims_block = ""
    claims = data.get("claims") or {}
    if isinstance(claims, dict) and claims:
        body = json.dumps(claims, indent=2, sort_keys=True)
        claims_block = "\n".join("    " + line for line in body.splitlines()) + "\n"

    output_block = ""
    output = data.get("output")
    if isinstance(output, str) and output.strip():
        output_block = (
            "<details><summary>check output</summary>\n\n"
            f"<pre>{html.escape(output)}</pre>\n\n"
            "</details>\n"
        )
    return claims_block, output_block


def _clean(value: str) -> str:
    return "".join(ch for ch in value if ch.isprintable() and ch not in "`\r\n")[:200]


def _summary(
    state: str, code: str, job: str, commit: str, source: str, claims: str, evidence: str
) -> str:
    text = (
        f"### oob: {_clean(state)}\n\n"
        "```text\n"
        f"job: {_clean(job)}\n"
        f"commit: {_clean(commit)}\n"
        f"state: {_clean(state)}\n"
        f"code: {_clean(code)}\n"
        f"source: {_clean(source)}\n"
        f"evidence: {_clean(evidence)}\n"
        "```\n"
    )
    if claims:
        text += "\n" + claims
    return text


def _decide() -> tuple[str, str, str, bool]:
    required = (os.environ.get("REQUIRED") or "true").lower() == "true"
    found = (os.environ.get("FOUND") or "false").lower() == "true"
    resolve_code = os.environ.get("RESOLVE_CODE") or ""

    if not required:
        return "not applicable", "OK", "success", False
    if (os.environ.get("EVIDENCE_STATUS") or "") == "invalid":
        return "unverified", "E_EVIDENCE_MISMATCH", "failure", False
    if not found:
        return "unverified", resolve_code or "E_NO_BLOCK", "failure", False

    raw_exit = (os.environ.get("VERIFY_EXIT") or "").strip()
    if not raw_exit:
        raise OutboardError("E_INTERNAL", "verify did not run")
    exit_code = int(raw_exit)
    if exit_code == 3:
        raise OutboardError("E_INTERNAL", "verification could not run; see the verify step")

    verdict = json.loads((Path(os.environ["RUNNER_TEMP"]) / "verdict.json").read_text())
    if exit_code == 0:
        return "verified", "OK", "success", True
    if exit_code == 1:
        return "failed", "OK", "failure", True
    if exit_code == 2:
        return "unverified", verdict.get("code", "E_INTERNAL"), "failure", False
    raise OutboardError("E_INTERNAL", f"unexpected verify exit code: {exit_code}")


def publish() -> int:
    state, code, conclusion, verified = _decide()
    repo = os.environ["GITHUB_REPOSITORY"]
    commit = os.environ["COMMIT"]
    job = os.environ["JOB"]
    check_name = os.environ.get("CHECK_NAME") or "oob"
    source = os.environ.get("SOURCE") or "none"
    temp = Path(os.environ["RUNNER_TEMP"])

    claims, output_block = _receipt_display(temp / "receipt.md") if verified else ("", "")
    evidence_status = os.environ.get("EVIDENCE_STATUS") or ""
    evidence_label = {"ok": "uploaded", "invalid": "invalid"}.get(evidence_status, "digest only")
    summary = _summary(state, code, job, commit, source, claims, evidence_label)

    payload = {
        "name": check_name,
        "head_sha": commit,
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": f"oob: {state}",
            "summary": summary,
            "text": output_block,
        },
    }
    _gh("api", "-X", "POST", f"repos/{repo}/check-runs", "--input", "-", stdin=json.dumps(payload))

    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as handle:
            handle.write(summary + "\n")

    pr = (os.environ.get("PR") or "0").strip()
    if pr.isdigit() and int(pr) > 0:
        login = BOT_LOGIN
        comments = _comments(repo, pr)
        existing = [
            comment
            for comment in comments
            if STATE_MARKER in (comment.get("body") or "")
            and (comment.get("user") or {}).get("login") == login
        ]
        body = f"{STATE_MARKER}\n{summary}\n{output_block}"
        if existing:
            _gh(
                "api",
                "-X",
                "PATCH",
                f"repos/{repo}/issues/comments/{existing[-1]['id']}",
                "--input",
                "-",
                stdin=json.dumps({"body": body}),
            )
        else:
            _gh(
                "api",
                "-X",
                "POST",
                f"repos/{repo}/issues/{pr}/comments",
                "--input",
                "-",
                stdin=json.dumps({"body": body}),
            )

    _set_output(verdict=state)
    return 0


def _safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    total = 0
    count = 0
    with tarfile.open(archive, "r:*") as tar:
        for member in tar.getmembers():
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts:
                raise OutboardError("E_EVIDENCE_ARCHIVE", f"unsafe path: {member.name}", 2)
            if member.issym() or member.islnk():
                raise OutboardError("E_EVIDENCE_ARCHIVE", f"link in archive: {member.name}", 2)
            if member.isdir():
                continue
            if not member.isfile():
                raise OutboardError("E_EVIDENCE_ARCHIVE", f"non-regular entry: {member.name}", 2)
            count += 1
            total += member.size
            if count > MAX_EVIDENCE_FILES or total > MAX_EVIDENCE_BYTES:
                raise OutboardError("E_EVIDENCE_ARCHIVE", "archive exceeds the size limit", 2)
            target = destination.joinpath(*name.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tar.extractfile(member)
            if source is None:
                raise OutboardError("E_EVIDENCE_ARCHIVE", f"unreadable entry: {member.name}", 2)
            with source, target.open("wb") as handle:
                shutil.copyfileobj(source, handle)


def evidence(receipt_path: str, archive_path: str, out_dir: str) -> int:
    """Unpack the operator's evidence and match it to the signed digest."""
    payload, _ = extract(Path(receipt_path).read_text(encoding="utf-8"))
    receipt = json.loads(payload)
    expected = (receipt.get("evidence") or {}).get("digest")
    if not isinstance(expected, str):
        raise OutboardError("E_INTERNAL", "receipt has no evidence digest")

    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    _safe_extract(Path(archive_path), out)
    count, digest = digest_directory(out)
    if digest != expected:
        raise OutboardError(
            "E_EVIDENCE_MISMATCH",
            f"evidence digest is {digest}, receipt says {expected}",
            2,
        )
    print(f"{count} files  {digest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["collect"]:
        return collect()
    if args == ["publish"]:
        return publish()
    if args and args[0] == "evidence":
        parser = argparse.ArgumentParser(prog="oob.workflow evidence", add_help=False)
        parser.add_argument("--receipt", required=True)
        parser.add_argument("--archive", required=True)
        parser.add_argument("--out", required=True)
        parsed, _ = parser.parse_known_args(args[1:])
        return evidence(parsed.receipt, parsed.archive, parsed.out)
    print("usage: python -m oob.workflow collect|publish", file=sys.stderr)
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
