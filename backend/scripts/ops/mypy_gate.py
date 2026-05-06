#!/usr/bin/env python3
"""
Mypy baseline gate script.

Prevents new mypy errors from being introduced while allowing gradual
reduction of existing errors. Uses a baseline file to track known errors.

Usage:
    python scripts/mypy_gate.py [--regenerate]

The baseline file (.mypy_baseline.txt) stores one fingerprint per line:
    <relative_path>:<line_number>

Exit codes:
    0 - no new errors (pass)
    1 - new errors introduced (fail)
    2 - baseline regeneration completed
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BASELINE_FILE = Path(__file__).parent.parent.parent / ".mypy_baseline.txt"
MYPY_ARGS = [
    "app/",
    "--ignore-missing-imports",
    "--show-error-codes",
    "--no-error-summary",
]


def run_mypy() -> set[str]:
    """Run mypy and return a set of error fingerprints."""
    result = subprocess.run(
        [sys.executable, "-m", "mypy", *MYPY_ARGS],
        capture_output=True,
        text=True,
    )
    # mypy exits with code 1 when errors are found, which is expected
    fingerprints: set[str] = set()
    for line in result.stdout.splitlines():
        # Parse lines like: app/file.py:42: error: Message [error-code]
        if ":" not in line:
            continue
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        file_path, line_no, rest = parts
        if "error:" not in rest:
            continue
        try:
            int(line_no)
        except ValueError:
            continue
        fingerprints.add(f"{file_path.strip()}:{line_no.strip()}")
    return fingerprints


def load_baseline() -> set[str]:
    """Load baseline fingerprints from file."""
    if not BASELINE_FILE.exists():
        return set()
    return {
        line.strip()
        for line in BASELINE_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def save_baseline(fingerprints: set[str]) -> None:
    """Save baseline fingerprints to file."""
    sorted_fps = sorted(fingerprints)
    BASELINE_FILE.write_text("\n".join(sorted_fps) + "\n", encoding="utf-8")
    print(f"Baseline regenerated: {len(sorted_fps)} errors tracked")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mypy baseline gate")
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate the baseline from current mypy output",
    )
    args = parser.parse_args()

    current = run_mypy()

    if args.regenerate:
        save_baseline(current)
        return 2

    baseline = load_baseline()
    new_errors = current - baseline
    fixed_errors = baseline - current

    if fixed_errors:
        print(f"PASS: {len(fixed_errors)} existing mypy error(s) fixed -- nice work!")
        # Optionally shrink baseline automatically
        remaining = current & baseline
        save_baseline(remaining | current)

    if new_errors:
        print(f"FAIL: {len(new_errors)} new mypy error(s) introduced:")
        for fp in sorted(new_errors):
            print(f"   {fp}")
        print(f"\nTotal: {len(current)} current errors vs {len(baseline)} baseline")
        print("Fix the errors above or run: python scripts/mypy_gate.py --regenerate")
        return 1

    print(f"PASS: mypy gate passed ({len(current)} errors, all in baseline)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
