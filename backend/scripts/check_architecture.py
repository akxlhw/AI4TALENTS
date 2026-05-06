"""
Architecture compliance checker for backend API endpoints.

Ensures strict layering: Endpoint -> Service -> Repository.
Endpoints (files under domains/*/api/) must NOT directly import:
  - Any *Repository class
  - Any *Collector class
  - Any *EmbeddingService class
  - LLMGateway
  - Low-level HTTP clients (GitHubClient, OpenAlexClient, etc.)
  - AsyncSessionLocal (session must be injected via Depends)
  - Domain models (except shared enums/schemas)

Usage:
    python scripts/check_architecture.py
    python scripts/check_architecture.py --update-baseline
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import sys
from pathlib import Path

# --- Configuration ---

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_GLOB = "app/domains/*/api/*.py"

# --- Rule definitions ---

# Modules that are ALWAYS allowed (schemas, core, shared enums, third-party)
ALLOWED_MODULE_PATTERNS = [
    r"app\.core\.",
    r"\.schemas\.",  # any domain's schemas are DTOs — Endpoints must import them
    r"\.models\.enums",
    r"fastapi",
    r"sqlalchemy",
    r"pydantic",
    r"typing",
]

# Banned: specific module substrings + the reason shown to developer
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

# Banned class / object names (substring match)
BANNED_NAME_PATTERNS: list[tuple[str, str]] = [
    ("Collector", "Collector must be accessed via Service only"),
    ("EmbeddingService", "EmbeddingService must be accessed via Service only"),
    ("LLMGateway", "LLMGateway is infrastructure — use Domain Service to encapsulate LLM calls"),
    ("GitHubClient", "HTTP client must be accessed via Service only"),
    ("OpenAlexClient", "HTTP client must be accessed via Service only"),
    ("AsyncSessionLocal", "Session must be injected via Depends(get_async_session)"),
]

# Explicitly allowed names (override bans above)
ALLOWED_NAMES = {
    "SearchService",      # academic search service lives in services/search/
    "ConfigService",      # shared service is allowed
    "UserService",        # shared service is allowed
    "AuditService",       # shared service is allowed
    "PermissionService",  # shared service is allowed
    "SystemConfigService",# shared service is allowed
    "OSRepositoryItem",   # schema DTO, name happens to contain 'Repository'
}


def _is_allowed_module(module: str) -> bool:
    """Check if module matches a global allow-list pattern."""
    import re
    for pat in ALLOWED_MODULE_PATTERNS:
        if re.search(pat, module):
            return True
    return False


def _is_banned(module: str, name: str) -> bool | str:
    """Return violation reason if banned, else False."""
    if name in ALLOWED_NAMES:
        return False

    # 1. Module-level bans (but skip services.llm.errors — exception classes are OK)
    if "services.llm.errors" not in module:
        for pattern, reason in BANNED_MODULE_RULES:
            if pattern in module:
                return reason

    # 2. Name-level bans
    for pattern, reason in BANNED_NAME_PATTERNS:
        if pattern in name:
            return reason

    return False


def _file_hash(path: str, module: str, name: str) -> str:
    """Stable hash for a violation entry."""
    content = f"{path}:{module}:{name}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def check_file(filepath: Path) -> list[dict]:
    """Check a single Python file for architecture violations."""
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
            # import x.y.z style — rarely used in our codebase, but handle it
            for alias in node.names:
                # alias.name is the full module path for "import" statements
                # We only care about app-level imports
                if not alias.name.startswith("app."):
                    continue
                module = alias.name
                if _is_allowed_module(module):
                    continue
                # For "import a.b.c", the "name" we check is the last segment
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
        help="Path to baseline file (default: .architecture_baseline.txt)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update baseline with current violations",
    )
    args = parser.parse_args()

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
        return 0

    # Print summary
    print("=" * 70)
    print("ARCHITECTURE COMPLIANCE CHECK")
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
        print("RESULT: FAILED — new architecture violations detected.")
        print("Fix the violations or run: python scripts/check_architecture.py --update-baseline")
        return 1

    print("RESULT: PASSED — no new architecture violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
