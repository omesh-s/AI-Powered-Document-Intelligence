import subprocess
import sys
from pathlib import Path


def test_run_eval_dry_run() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "evals" / "run_eval.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--dry-run", "--eval-set", str(root / "evals" / "sample_eval_set.json")],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Dry run OK" in proc.stdout
