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


def build(target: Path = TARGET) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "app"
        shutil.copytree(ROOT / "src" / "oob", stage / "oob", ignore=IGNORE)
        (stage / "__main__.py").write_text(
            "import sys\nfrom oob.cli import main\n\nsys.exit(main())\n",
            encoding="utf-8",
        )
        zipapp.create_archive(
            stage,
            target,
            interpreter="/usr/bin/env python3",
            compressed=True,
        )
    return target


if __name__ == "__main__":
    print(build(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET))
