"""Pre-commit hook runner for backend — lightweight architecture check only.

Ruff/black/mypy are intentionally skipped here because:
1. They can be slow on large codebases (mypy >10s)
2. The existing codebase has legacy lint debt that would block every commit
3. Run full lint via: .\scripts\local_ci.ps1

This hook ONLY checks architecture compliance (cross-layer imports),
which is fast (<1s) and has zero legacy violations for new code.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"


def main() -> int:
    print(">>> uv run python scripts/check_architecture.py")
    rc = subprocess.run(
        ["uv", "run", "python", "scripts/check_architecture.py"],
        cwd=BACKEND_DIR,
    ).returncode
    if rc != 0:
        print(
            "\n[FAIL] Architecture check failed.\n"
            "       Fix cross-layer imports or run: cd backend && uv run python scripts/check_architecture.py",
            file=sys.stderr,
        )
        return rc
    print("\n[PASS] Architecture check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
