"""
Architecture compliance checker for backend API endpoints.

Checks two independent rules:

1. Endpoint Layering: files under domains/*/api/ must NOT directly import:
   - Any *Repository class
   - Any *Collector class
   - Any *EmbeddingService class
   - LLMGateway
   - Low-level HTTP clients (GitHubClient, OpenAlexClient, etc.)
   - AsyncSessionLocal
   - Domain models (except shared enums/schemas)

2. Cross-Domain Dependencies (ZERO tolerance — no baseline):
   The shared infrastructure layer must NOT import from business domains.

   Allowed:  academic → shared     open_source → shared     shared → shared
   Banned:   shared → academic     shared → open_source

Usage:
    python scripts/check_architecture.py
    python scripts/check_architecture.py --update-baseline
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import re
import sys
from pathlib import Path

# --- Configuration ---

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_GLOB = "app/domains/*/api/*.py"
DOMAIN_GLOB = "app/domains/*/**/*.py"

# --- Rule definitions: Endpoint Layering ---

ALLOWED_MODULE_PATTERNS = [
    r"app\.core\.",
    r"\.schemas\.",
    r"\.models\.enums",
    r"fastapi",
    r"sqlalchemy",
    r"pydantic",
    r"typing",
]

BANNED_MODULE_RULES: list[tuple[str, str]] = [
    ("repositories.", "Repository layer must be accessed via Service only"),
    ("collectors.", "Collector must be accessed via Service only"),
    ("builders.", "Builder must be accessed via Service only"),
    (".models.", "Domain models must not leak into Endpoint layer"),
    ("services.llm", "LLMGateway is infrastructure — use Domain Service to encapsulate LLM calls"),
    ("services.open_source_embedding_service", "EmbeddingService must be accessed via Service only"),
    ("services.embedding.embedding_service", "EmbeddingService must be accessed via Service only"),
    ("services.github_client", "HTTP client must be accessed via Service only"),
    ("services.openalex_client", "HTTP client must be accessed via Service only"),
    ("services.collect.", "Collect orchestrator must be accessed via Service only"),
]

BANNED_NAME_PATTERNS: list[tuple[str, str]] = [
    ("Collector", "Collector must be accessed via Service only"),
    ("EmbeddingService", "EmbeddingService must be accessed via Service only"),
    ("LLMGateway", "LLMGateway is infrastructure — use Domain Service to encapsulate LLM calls"),
    ("GitHubClient", "HTTP client must be accessed via Service only"),
    ("OpenAlexClient", "HTTP client must be accessed via Service only"),
    ("AsyncSessionLocal", "Session must be injected via Depends(get_async_session)"),
]

ALLOWED_NAMES = {
    "SearchService",
    "ConfigService",
    "UserService",
    "AuditService",
    "PermissionService",
    "SystemConfigService",
    "OSRepositoryItem",
}

# --- Rule definitions: Cross-Domain Dependencies ---

# shared/ 中的文件禁止 import 这些业务域模块
CROSS_DOMAIN_BANNED: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"app\.domains\.academic\.(?!models\.enums)"),
        "shared infrastructure must NOT import academic business domain — "
        "move code to academic/ or use dependency inversion",
    ),
    (
        re.compile(r"app\.domains\.open_source\."),
        "shared infrastructure must NOT import open_source business domain — "
        "move code to open_source/ or use dependency inversion",
    ),
]

# shared 内部允许 import 的模式（白名单）
CROSS_DOMAIN_ALLOWED_PATTERNS = [
    r"app\.domains\.shared\.",
    r"app\.core\.",
    r"app\.domains\.academic\.models\.enums",
]


def _is_allowed_module(module: str) -> bool:
    """Check if module matches a global allow-list pattern."""
    for pat in ALLOWED_MODULE_PATTERNS:
        if re.search(pat, module):
            return True
    return False


def _is_banned(module: str, name: str) -> bool | str:
    """Return violation reason if banned, else False."""
    if name in ALLOWED_NAMES:
        return False

    if "services.llm.errors" not in module:
        for pattern, reason in BANNED_MODULE_RULES:
            if pattern in module:
                return reason

    for pattern, reason in BANNED_NAME_PATTERNS:
        if pattern in name:
            return reason

    return False


def _file_hash(path: str, module: str, name: str) -> str:
    """Stable hash for a violation entry."""
    content = f"{path}:{module}:{name}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def check_file(filepath: Path) -> list[dict]:
    """Check a single Python file for Endpoint-layer architecture violations."""
    violations = []
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except SyntaxError as exc:
        violations.append({
            "file": str(filepath.relative_to(PROJECT_ROOT)),
            "line": exc.lineno or 1,
            "module": "<syntax-error>",
            "name": "<syntax-error>",
            "reason": f"SyntaxError: {exc}",
        })
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _is_allowed_module(module):
                continue

            for alias in node.names:
                name = alias.name
                reason = _is_banned(module, name)
                if reason:
                    violations.append({
                        "file": str(filepath.relative_to(PROJECT_ROOT)),
                        "line": node.lineno,
                        "module": module,
                        "name": name,
                        "reason": reason,
                    })
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if not alias.name.startswith("app."):
                    continue
                module = alias.name
                if _is_allowed_module(module):
                    continue
                name = alias.asname or alias.name.split(".")[-1]
                reason = _is_banned(module, name)
                if reason:
                    violations.append({
                        "file": str(filepath.relative_to(PROJECT_ROOT)),
                        "line": node.lineno,
                        "module": module,
                        "name": name,
                        "reason": reason,
                    })
    return violations


def _is_cross_domain_allowed(module: str) -> bool:
    """Check if a module import is allowed from shared/ (whitelisted)."""
    for pat in CROSS_DOMAIN_ALLOWED_PATTERNS:
        if re.search(pat, module):
            return True
    return False


def check_cross_domain(filepath: Path) -> list[dict]:
    """
    Check that shared/ domain does NOT import from business domains.
    Zero tolerance — no baseline for this check.
    """
    violations = []

    # Only check files under domains/shared/
    relative = filepath.relative_to(PROJECT_ROOT)
    if not str(relative).startswith("app/domains/shared/"):
        return violations

    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except SyntaxError as exc:
        violations.append({
            "file": str(relative),
            "line": exc.lineno or 1,
            "module": "<syntax-error>",
            "name": "<syntax-error>",
            "reason": f"SyntaxError: {exc}",
        })
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _is_cross_domain_allowed(module):
                continue
            for pattern, reason in CROSS_DOMAIN_BANNED:
                if pattern.search(module):
                    for alias in node.names:
                        violations.append({
                            "file": str(relative),
                            "line": node.lineno,
                            "module": module,
                            "name": alias.name,
                            "reason": reason,
                        })
                    break  # only report once per import line

        elif isinstance(node, ast.Import):
            for alias in node.names:
                if not alias.name.startswith("app."):
                    continue
                if _is_cross_domain_allowed(alias.name):
                    continue
                for pattern, reason in CROSS_DOMAIN_BANNED:
                    if pattern.search(alias.name):
                        name = alias.asname or alias.name.split(".")[-1]
                        violations.append({
                            "file": str(relative),
                            "line": node.lineno,
                            "module": alias.name,
                            "name": name,
                            "reason": reason,
                        })
                        break

    return violations


def load_baseline(baseline_path: Path) -> set[str]:
    """Load baseline hashes."""
    if not baseline_path.exists():
        return set()
    lines = baseline_path.read_text(encoding="utf-8").strip().splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def save_baseline(baseline_path: Path, hashes: set[str]) -> None:
    """Save baseline hashes."""
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    content = "# Architecture compliance baseline\n# Generated by scripts/check_architecture.py --update-baseline\n\n"
    content += "\n".join(sorted(hashes))
    content += "\n"
    baseline_path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check API endpoint architecture compliance")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=PROJECT_ROOT / ".architecture_baseline.txt",
        help="Path to baseline file for Endpoint-layer checks (default: .architecture_baseline.txt)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update baseline with current Endpoint-layer violations",
    )
    args = parser.parse_args()

    exit_code = 0

    # ================================================================
    # CHECK 1: Cross-Domain Dependencies (ZERO tolerance)
    # ================================================================
    domain_files = list(PROJECT_ROOT.glob(DOMAIN_GLOB))
    cross_domain_violations: list[dict] = []
    for filepath in domain_files:
        if filepath.name == "__init__.py":
            continue
        cross_domain_violations.extend(check_cross_domain(filepath))

    if cross_domain_violations:
        print("=" * 70)
        print("CROSS-DOMAIN DEPENDENCY CHECK")
        print("=" * 70)
        print(f"Scanned files: {len(domain_files)}")
        print(f"Violations: {len(cross_domain_violations)}")
        print()
        print("CRITICAL — shared infrastructure must NOT depend on business domains:")
        print("-" * 70)
        for v in cross_domain_violations:
            print(
                f"  {v['file']}:{v['line']}\n"
                f"    from {v['module']} import {v['name']}\n"
                f"    reason: {v['reason']}"
            )
        print()
        print("RESULT: FAILED — cross-domain dependency violations detected.")
        print("Fix the violations before committing.")
        print()
        exit_code = 1
    else:
        print("=" * 70)
        print("CROSS-DOMAIN DEPENDENCY CHECK")
        print("=" * 70)
        print(f"Scanned files: {len(domain_files)}")
        print("RESULT: PASSED — no cross-domain dependency violations.")
        print()

    # ================================================================
    # CHECK 2: Endpoint Layering (baseline-tolerant)
    # ================================================================
    api_files = list(PROJECT_ROOT.glob(API_GLOB))
    if not api_files:
        print(f"ERROR: No API files found matching {API_GLOB}")
        return 1

    all_violations: list[dict] = []
    for filepath in api_files:
        if filepath.name == "__init__.py":
            continue
        all_violations.extend(check_file(filepath))

    baseline_hashes = load_baseline(args.baseline)
    new_violations = []
    known_violations = []

    for v in all_violations:
        h = _file_hash(v["file"], v["module"], v["name"])
        if h in baseline_hashes:
            known_violations.append(v)
        else:
            new_violations.append(v)

    if args.update_baseline:
        all_hashes = {_file_hash(v["file"], v["module"], v["name"]) for v in all_violations}
        save_baseline(args.baseline, all_hashes)
        print(f"Baseline updated: {len(all_hashes)} violations recorded")
        print(f"  - New: {len(new_violations)}")
        print(f"  - Known: {len(known_violations)}")
        # Return cross-domain exit code even when updating baseline
        return exit_code

    print("=" * 70)
    print("ENDPOINT LAYERING CHECK")
    print("=" * 70)
    print(f"Scanned files: {len(api_files)}")
    print(f"Total violations: {len(all_violations)}")
    print(f"Known (baseline): {len(known_violations)}")
    print(f"NEW violations: {len(new_violations)}")
    print()

    if new_violations:
        print("NEW violations (these must be fixed or baseline updated):")
        print("-" * 70)
        for v in new_violations:
            print(
                f"  {v['file']}:{v['line']}\n"
                f"    from {v['module']} import {v['name']}\n"
                f"    reason: {v['reason']}"
            )
        print()
        exit_code = 1

    if known_violations:
        print("Known violations (existing technical debt):")
        print("-" * 70)
        for v in known_violations:
            print(
                f"  {v['file']}:{v['line']}\n"
                f"    from {v['module']} import {v['name']}"
            )
        print()

    if new_violations:
        print("RESULT: FAILED — new Endpoint-layer violations detected.")
        print("Fix the violations or run: python scripts/check_architecture.py --update-baseline")
    else:
        print("RESULT: PASSED — no new Endpoint-layer violations.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
