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
    text = workflow._summary("verified", "OK", "job```x", "a" * 40, "comments", "")
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
