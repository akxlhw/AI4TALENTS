"""Regression tests for the endpoint-layering rule in scripts/check_architecture.py.

Locks the fix for the allow-list short-circuit: banned names (AsyncSessionLocal,
*Collector, ...) must be flagged even when imported from an allow-listed module
such as app.core.*.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_architecture", BACKEND_ROOT / "scripts" / "check_architecture.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check_source(
    checker: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> list[dict]:
    monkeypatch.setattr(checker, "PROJECT_ROOT", tmp_path)
    target = tmp_path / "app" / "domains" / "academic" / "api" / "sample_endpoint.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    return checker.check_file(target)


def test_async_session_local_from_core_is_flagged(
    checker: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """from app.core.database import AsyncSessionLocal must be a violation."""
    violations = _check_source(
        checker, tmp_path, monkeypatch, "from app.core.database import AsyncSessionLocal\n"
    )
    assert len(violations) == 1
    assert violations[0]["name"] == "AsyncSessionLocal"


def test_plain_core_imports_are_allowed(
    checker: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    violations = _check_source(
        checker,
        tmp_path,
        monkeypatch,
        "from app.core.config import settings\nfrom app.core.database import get_async_session\n",
    )
    assert violations == []


def test_shared_enums_import_is_allowed(
    checker: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    violations = _check_source(
        checker, tmp_path, monkeypatch, "from app.domains.shared.models.enums import RoleType\n"
    )
    assert violations == []


def test_repository_import_is_flagged(
    checker: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    violations = _check_source(
        checker,
        tmp_path,
        monkeypatch,
        "from app.domains.academic.repositories.x import TalentRepository\n",
    )
    assert len(violations) == 1
