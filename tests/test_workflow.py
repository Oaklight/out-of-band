from __future__ import annotations

import json
from pathlib import Path

import pytest

from outboard import workflow
from outboard.errors import OutboardError


def test_collect_uses_the_input_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out"
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/widget")
    monkeypatch.setenv("RECEIPT", "the receipt")
    monkeypatch.setenv("PR", "0")
    assert workflow.collect() == 0
    assert (tmp_path / "receipt.md").read_text() == "the receipt"
    assert "found=true" in output.read_text()


def test_collect_ignores_untrusted_comments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "out"
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/widget")
    monkeypatch.setenv("RECEIPT", "")
    monkeypatch.setenv("PR", "7")
    monkeypatch.setenv("TRUSTED", "")
    honest = {
        "body": "<!-- receipt:v1 -->\nblock",
        "author_association": "OWNER",
        "user": {"login": "owner"},
    }
    stranger = {
        "body": "<!-- receipt:v1 -->\ngarbage",
        "author_association": "NONE",
        "user": {"login": "stranger"},
    }
    monkeypatch.setattr(workflow, "_comments", lambda repo, pr: [stranger, honest])
    assert workflow.collect() == 0
    assert (tmp_path / "receipt.md").read_text() == honest["body"]


def test_collect_rejects_disagreeing_trusted_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "out"
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/widget")
    monkeypatch.setenv("RECEIPT", "")
    monkeypatch.setenv("PR", "7")
    monkeypatch.setenv("TRUSTED", "")
    first = {
        "body": '<!-- receipt:v1 -->\n```json\n{"a":1}\n```\n```ssh-signature\nAAA\n```\n',
        "author_association": "MEMBER",
        "user": {"login": "one"},
    }
    second = {
        "body": '<!-- receipt:v1 -->\n```json\n{"a":2}\n```\n```ssh-signature\nAAA\n```\n',
        "author_association": "MEMBER",
        "user": {"login": "two"},
    }
    monkeypatch.setattr(workflow, "_comments", lambda repo, pr: [first, second])
    assert workflow.collect() == 0
    assert "code=E_MULTI_BLOCK" in output.read_text()


@pytest.mark.parametrize(
    ("required", "found", "verify_exit", "verdict", "expected"),
    [
        ("false", "false", "", None, ("not applicable", "OK", "success", False)),
        ("true", "false", "", None, ("unverified", "E_NO_BLOCK", "action_required", False)),
        ("true", "true", "0", {"code": "OK"}, ("verified", "OK", "success", True)),
        ("true", "true", "1", {"code": "OK"}, ("failed", "OK", "failure", True)),
        (
            "true",
            "true",
            "2",
            {"code": "E_NO_PRINCIPAL"},
            ("unverified", "E_NO_PRINCIPAL", "action_required", False),
        ),
    ],
)
def test_decide(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    required: str,
    found: str,
    verify_exit: str,
    verdict: dict | None,
    expected: tuple,
) -> None:
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("REQUIRED", required)
    monkeypatch.setenv("FOUND", found)
    monkeypatch.setenv("VERIFY_EXIT", verify_exit)
    monkeypatch.setenv("RESOLVE_CODE", "")
    if verdict is not None:
        (tmp_path / "verdict.json").write_text(json.dumps(verdict))
    assert workflow._decide() == expected


def test_decide_refuses_a_tool_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("REQUIRED", "true")
    monkeypatch.setenv("FOUND", "true")
    monkeypatch.setenv("VERIFY_EXIT", "3")
    with pytest.raises(OutboardError) as caught:
        workflow._decide()
    assert caught.value.code == "E_INTERNAL"


def test_summary_cannot_break_the_fence() -> None:
    text = workflow._summary("verified", "OK", "job```x", "a" * 40, "comments", "", "digest only")
    assert "```x" not in text
    assert text.count("```") == 2


def test_publish_creates_a_check_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[tuple[str, ...], str | None]] = []
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/widget")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "out"))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary"))
    monkeypatch.setenv("REQUIRED", "true")
    monkeypatch.setenv("FOUND", "true")
    monkeypatch.setenv("VERIFY_EXIT", "0")
    monkeypatch.setenv("COMMIT", "a" * 40)
    monkeypatch.setenv("JOB", "smoke")
    monkeypatch.setenv("CHECK_NAME", "gate")
    monkeypatch.setenv("PR", "0")
    (tmp_path / "verdict.json").write_text('{"verdict":"pass","code":"OK"}')

    def fake_gh(*args: str, stdin: str | None = None) -> str:
        calls.append((args, stdin))
        return ""

    monkeypatch.setattr(workflow, "_gh", fake_gh)
    assert workflow.publish() == 0
    payload = json.loads(next(stdin for args, stdin in calls if "--input" in args and stdin))
    assert payload["conclusion"] == "success"
    assert payload["head_sha"] == "a" * 40
    assert payload["name"] == "gate"
    assert "verified" in (tmp_path / "summary").read_text()
    assert "verdict=verified" in (tmp_path / "out").read_text()


def _receipt_comment(commit: str, signature: str = "AAA", job: str = "smoke") -> dict:
    payload = json.dumps(
        {"schema": "receipt/v1", "commit": commit, "job": job, "result": "pass"},
        separators=(",", ":"),
    )
    body = f"<!-- receipt:v1 -->\n```json\n{payload}\n```\n```ssh-signature\n{signature}\n```\n"
    return {"body": body, "author_association": "OWNER", "user": {"login": "operator"}}


def _collect_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, commit: str, job: str = ""
) -> Path:
    output = tmp_path / "out"
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/widget")
    monkeypatch.setenv("RECEIPT", "")
    monkeypatch.setenv("PR", "7")
    monkeypatch.setenv("TRUSTED", "")
    monkeypatch.setenv("COMMIT", commit)
    monkeypatch.setenv("JOB", job)
    return output


def test_collect_ignores_receipts_for_another_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A re-run after a new push must not be poisoned by the old receipt."""
    head = "a" * 40
    previous = "b" * 40
    output = _collect_env(tmp_path, monkeypatch, head)
    comments = [_receipt_comment(previous), _receipt_comment(head)]
    monkeypatch.setattr(workflow, "_comments", lambda repo, pr: comments)

    assert workflow.collect() == 0
    assert "found=true" in output.read_text()
    assert head in (tmp_path / "receipt.md").read_text()


def test_collect_reports_wrong_commit_when_only_stale_receipts_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = _collect_env(tmp_path, monkeypatch, "a" * 40)
    comments = [_receipt_comment("b" * 40)]
    monkeypatch.setattr(workflow, "_comments", lambda repo, pr: comments)

    assert workflow.collect() == 0
    text = output.read_text()
    assert "found=false" in text
    assert "code=E_WRONG_COMMIT" in text


def test_collect_selects_the_block_for_the_expected_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two jobs may attest one commit; each gate reads only its own block."""
    head = "a" * 40
    output = _collect_env(tmp_path, monkeypatch, head, job="alpha")
    comments = [
        _receipt_comment(head, "AAA", job="alpha"),
        _receipt_comment(head, "BBB", job="beta"),
    ]
    monkeypatch.setattr(workflow, "_comments", lambda repo, pr: comments)

    assert workflow.collect() == 0
    assert "found=true" in output.read_text()
    assert '"job":"alpha"' in (tmp_path / "receipt.md").read_text()


def test_collect_reports_wrong_job_when_only_other_jobs_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = "a" * 40
    output = _collect_env(tmp_path, monkeypatch, head, job="gamma")
    comments = [_receipt_comment(head, "AAA", job="alpha")]
    monkeypatch.setattr(workflow, "_comments", lambda repo, pr: comments)

    assert workflow.collect() == 0
    text = output.read_text()
    assert "found=false" in text
    assert "code=E_WRONG_JOB" in text


def test_collect_still_rejects_disagreeing_blocks_for_the_same_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = "a" * 40
    output = _collect_env(tmp_path, monkeypatch, head)
    comments = [_receipt_comment(head, "AAA"), _receipt_comment(head, "BBB")]
    monkeypatch.setattr(workflow, "_comments", lambda repo, pr: comments)

    assert workflow.collect() == 0
    assert "code=E_MULTI_BLOCK" in output.read_text()


def test_collect_skips_unparseable_blocks_when_a_commit_is_expected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = "a" * 40
    output = _collect_env(tmp_path, monkeypatch, head)
    truncated = {
        "body": "<!-- receipt:v1 -->\n```json\n{not json}\n```\n",
        "author_association": "OWNER",
        "user": {"login": "operator"},
    }
    monkeypatch.setattr(workflow, "_comments", lambda repo, pr: [truncated, _receipt_comment(head)])

    assert workflow.collect() == 0
    assert "found=true" in output.read_text()


def test_collect_reports_the_parse_error_when_every_block_is_malformed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = _collect_env(tmp_path, monkeypatch, "a" * 40)
    broken = {
        "body": '<!-- receipt:v1 -->\n```json\n{"schema":"receipt/v1"}\n```\n',
        "author_association": "OWNER",
        "user": {"login": "operator"},
    }
    monkeypatch.setattr(workflow, "_comments", lambda repo, pr: [broken])

    assert workflow.collect() == 0
    text = output.read_text()
    assert "found=false" in text
    assert "code=E_BAD_FENCE" in text


def test_publish_carries_the_signed_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[tuple[str, ...], str | None]] = []
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/widget")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "out"))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary"))
    monkeypatch.setenv("REQUIRED", "true")
    monkeypatch.setenv("FOUND", "true")
    monkeypatch.setenv("VERIFY_EXIT", "0")
    monkeypatch.setenv("COMMIT", "a" * 40)
    monkeypatch.setenv("JOB", "smoke")
    monkeypatch.setenv("CHECK_NAME", "gate")
    monkeypatch.setenv("PR", "0")
    (tmp_path / "verdict.json").write_text('{"verdict":"pass","code":"OK"}')
    payload = json.dumps(
        {"schema": "receipt/v2", "commit": "a" * 40, "output": "<script>alert(1)</script>"},
        separators=(",", ":"),
    )
    (tmp_path / "receipt.md").write_text(
        f"<!-- receipt:v1 -->\n```json\n{payload}\n```\n```ssh-signature\nAAA\n```\n",
        encoding="utf-8",
    )

    def fake_gh(*args: str, stdin: str | None = None) -> str:
        calls.append((args, stdin))
        return ""

    monkeypatch.setattr(workflow, "_gh", fake_gh)
    assert workflow.publish() == 0
    check = json.loads(next(stdin for args, stdin in calls if "--input" in args and stdin))
    assert "<details>" in check["output"]["text"]
    assert "&lt;script&gt;" in check["output"]["text"]


def test_evidence_round_trip(tmp_path: Path, keypair: Path) -> None:
    source = tmp_path / "evidence"
    (source / "nested").mkdir(parents=True)
    (source / "run.log").write_text("ok\n", encoding="utf-8")
    (source / "nested" / "result.json").write_text("{}", encoding="utf-8")

    from outboard.evidence import digest_directory, pack_directory

    count, digest = digest_directory(source)
    assert count == 2
    archive = tmp_path / "evidence.tgz"
    assert pack_directory(source, archive) == (count, digest)

    receipt = tmp_path / "receipt.md"
    payload = json.dumps(
        {"schema": "receipt/v2", "evidence": {"count": count, "digest": digest}},
        separators=(",", ":"),
    )
    receipt.write_text(
        f"<!-- receipt:v1 -->\n```json\n{payload}\n```\n```ssh-signature\nAAA\n```\n",
        encoding="utf-8",
    )
    out = tmp_path / "unpacked"
    assert workflow.evidence(str(receipt), str(archive), str(out)) == 0
    assert (out / "nested" / "result.json").read_text() == "{}"


def test_evidence_mismatch_is_rejected(tmp_path: Path, keypair: Path) -> None:
    from outboard.evidence import pack_directory

    source = tmp_path / "evidence"
    source.mkdir()
    (source / "run.log").write_text("ok\n", encoding="utf-8")
    archive = tmp_path / "evidence.tgz"
    pack_directory(source, archive)

    receipt = tmp_path / "receipt.md"
    payload = json.dumps(
        {"schema": "receipt/v1", "evidence": {"count": 1, "digest": "sha256:" + "0" * 64}},
        separators=(",", ":"),
    )
    receipt.write_text(
        f"<!-- receipt:v1 -->\n```json\n{payload}\n```\n```ssh-signature\nAAA\n```\n",
        encoding="utf-8",
    )
    with pytest.raises(OutboardError) as caught:
        workflow.evidence(str(receipt), str(archive), str(tmp_path / "out"))
    assert caught.value.code == "E_EVIDENCE_MISMATCH"


def test_evidence_archive_cannot_escape(tmp_path: Path) -> None:
    import io
    import tarfile

    archive = tmp_path / "evil.tgz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo("../escape")
        info.size = 1
        tar.addfile(info, io.BytesIO(b"x"))
    receipt = tmp_path / "receipt.md"
    payload = json.dumps(
        {"schema": "receipt/v1", "evidence": {"count": 1, "digest": "sha256:" + "0" * 64}},
        separators=(",", ":"),
    )
    receipt.write_text(
        f"<!-- receipt:v1 -->\n```json\n{payload}\n```\n```ssh-signature\nAAA\n```\n",
        encoding="utf-8",
    )
    with pytest.raises(OutboardError) as caught:
        workflow.evidence(str(receipt), str(archive), str(tmp_path / "out"))
    assert caught.value.code == "E_EVIDENCE_ARCHIVE"


def test_decide_rejects_mismatched_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("REQUIRED", "true")
    monkeypatch.setenv("FOUND", "true")
    monkeypatch.setenv("VERIFY_EXIT", "0")
    monkeypatch.setenv("EVIDENCE_STATUS", "invalid")
    (tmp_path / "verdict.json").write_text('{"code":"OK"}')
    assert workflow._decide() == ("unverified", "E_EVIDENCE_MISMATCH", "action_required", False)
