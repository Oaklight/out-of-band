"""Error codes and exit statuses.

Every failure carries a stable code. Exit codes are defined in SPEC.md §4.1:
0 pass, 1 valid fail, 2 absent or invalid receipt, 3 usage or internal error.
"""

from __future__ import annotations

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_UNVERIFIED = 2
EXIT_ERROR = 3


class OutboardError(Exception):
    """A handled failure with a stable code and an exit status."""

    def __init__(self, code: str, message: str, exit_code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code

    def __str__(self) -> str:
        return self.message
