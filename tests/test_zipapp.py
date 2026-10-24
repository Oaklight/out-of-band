import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_zipapp_reports_version(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_zipapp import build

    target = build(tmp_path / "oob.pyz")
    result = subprocess.run(
        [sys.executable, str(target), "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("oob ")
