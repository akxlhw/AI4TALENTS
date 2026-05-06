"""Pre-commit hook runner for frontend checks (cross-platform)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def run(cmd: list[str]) -> int:
    print(f"\n>>> {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=FRONTEND_DIR).returncode


def main() -> int:
    rc = run(["npm", "run", "lint"])
    if rc != 0:
        print("\n[FAIL] npm run lint", file=sys.stderr)
        return rc

    print("\n[PASS] Frontend pre-commit checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
