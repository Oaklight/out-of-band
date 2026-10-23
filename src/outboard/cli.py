"""Command line entry point."""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

from . import __version__
from .errors import EXIT_ERROR, OutboardError
from .sign import sign


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
    sign_parser.add_argument("--out", type=Path, help="write the block here instead of stdout")
    return parser


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
            )
            if args.out:
                args.out.write_text(block, encoding="utf-8")
                print(f"wrote {args.out}", file=sys.stderr)
            else:
                sys.stdout.write(block)
            return 0
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
