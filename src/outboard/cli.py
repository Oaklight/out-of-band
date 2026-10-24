"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

from . import __version__
from .errors import EXIT_ERROR, OutboardError
from .evidence import pack_directory
from .sign import sign
from .verify import verify


class _Parser(argparse.ArgumentParser):
    """argparse exits 2 on usage errors; SPEC.md §4.1 wants 3."""

    def error(self, message: str) -> None:  # type: ignore[override]
        raise OutboardError("E_USAGE", message)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="outboard",
        description="Out-of-band receipts for CI gates.",
    )
    parser.add_argument("--version", action="version", version=f"outboard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    sign_parser = sub.add_parser("sign", help="sign a receipt for one commit")
    sign_parser.add_argument("--job", required=True, help="job name the consumer expects")
    sign_parser.add_argument("--commit", required=True, help="full 40-hex commit SHA")
    sign_parser.add_argument("--result", required=True, choices=("pass", "fail"))
    sign_parser.add_argument("--evidence-dir", required=True)
    sign_parser.add_argument("--key", required=True, help="private key path")
    sign_parser.add_argument("--repo", help="owner/name; defaults to the origin remote")
    sign_parser.add_argument(
        "--claims",
        action="append",
        default=[],
        metavar="K=V",
        help="consumer claim, repeatable",
    )
    sign_parser.add_argument("--allow-dirty", action="store_true")
    sign_parser.add_argument(
        "--output-file",
        help="curated check output to carry in the receipt (v2, at most 4 KiB)",
    )
    sign_parser.add_argument("--out", type=Path, help="write the block here instead of stdout")

    pack_parser = sub.add_parser("pack", help="package an evidence directory")
    pack_parser.add_argument("--evidence-dir", required=True)
    pack_parser.add_argument("--out", required=True, type=Path)
    pack_parser.add_argument("--json", action="store_true")

    verify_parser = sub.add_parser("verify", help="verify a receipt block")
    verify_parser.add_argument("--block", required=True, help="file holding the comment or block")
    verify_parser.add_argument("--allowed-signers", required=True)
    verify_parser.add_argument("--repo", required=True, help="expected owner/name")
    verify_parser.add_argument("--commit", required=True, help="expected 40-hex head")
    verify_parser.add_argument("--expect-job", required=True)
    verify_parser.add_argument("--expect-tree")
    verify_parser.add_argument("--json", action="store_true", help="one machine-readable line")
    return parser


def _verify_command(args: argparse.Namespace) -> int:
    try:
        result = verify(
            block_path=args.block,
            allowed_signers=args.allowed_signers,
            repo=args.repo,
            commit=args.commit,
            job=args.expect_job,
            tree=args.expect_tree,
        )
    except OutboardError as exc:
        if args.json:
            verdict = "unverified" if exc.exit_code == 2 else "error"
            print(
                json.dumps(
                    {
                        "verdict": verdict,
                        "code": exc.code,
                        "repo": None,
                        "commit": None,
                        "job": None,
                    },
                    separators=(",", ":"),
                )
            )
        print(f"error: {exc.code}: {exc.message}", file=sys.stderr)
        return exc.exit_code

    if args.json:
        print(json.dumps(result, separators=(",", ":")))
    else:
        print(f"receipt: {result['verdict']} (verified)")
        print(f"repo: {result['repo']}")
        print(f"commit: {result['commit']}")
        print(f"job: {result['job']}")
    return 0 if result["verdict"] == "pass" else 1


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if args.command == "sign":
            block = sign(
                job=args.job,
                commit=args.commit,
                result=args.result,
                evidence_dir=args.evidence_dir,
                key=args.key,
                repo=args.repo,
                claims=args.claims,
                allow_dirty=args.allow_dirty,
                output_file=args.output_file,
            )
            if args.out:
                args.out.write_text(block, encoding="utf-8")
                print(f"wrote {args.out}", file=sys.stderr)
            else:
                sys.stdout.write(block)
            return 0
        if args.command == "pack":
            count, digest = pack_directory(args.evidence_dir, args.out)
            if args.json:
                print(json.dumps({"count": count, "digest": digest}, separators=(",", ":")))
            else:
                print(f"{count} files  {digest}")
            return 0
        if args.command == "verify":
            return _verify_command(args)
        raise OutboardError("E_USAGE", f"unknown command: {args.command}")
    except OutboardError as exc:
        print(f"error: {exc.code}: {exc.message}", file=sys.stderr)
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 - the CLI must not leak a traceback by default
        if os.environ.get("OUTBOARD_DEBUG"):
            traceback.print_exc()
        print(f"error: E_INTERNAL: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
