"""Build `dist/oob.pyz`, a single file that runs on a bare python3.

For hosts where installing a wheel is awkward or disallowed: no pip, no venv,
no package directory. The archive holds the package plus a root `__main__.py`.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "dist" / "oob.pyz"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")

# A shebang can name only one interpreter, and /usr/bin/env is not everywhere
# (NixOS, minimal images). This prefix is a POSIX shell launcher: the kernel
# runs /bin/sh, which finds a Python >= 3.11 and re-executes the archive.
# Python's zipimport ignores bytes before the ZIP header, so `python3 oob.pyz`
# still works, including on Windows.
LAUNCHER = """#!/bin/sh
# out-of-band: find Python 3.11+ and run this archive.
for candidate in python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    exec "$candidate" "$0" "$@"
  fi
done
echo "out-of-band needs Python 3.11 or newer." >&2
echo "Try: python3.11 $0 --version" >&2
exit 1
"""


def build(target: Path = TARGET) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "app"
        shutil.copytree(ROOT / "src" / "oob", stage / "oob", ignore=IGNORE)
        (stage / "__main__.py").write_text(
            "import sys\nfrom oob.cli import main\n\nsys.exit(main())\n",
            encoding="utf-8",
        )
        archive = Path(tmp) / "oob.zip"
        zipapp.create_archive(stage, archive, interpreter=None, compressed=True)
        target.write_bytes(LAUNCHER.encode("utf-8") + archive.read_bytes())
        target.chmod(0o755)
    return target


if __name__ == "__main__":
    print(build(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET))
