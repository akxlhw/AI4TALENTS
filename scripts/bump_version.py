#!/usr/bin/env python3
"""Bump version number across all project files.

Usage:
    python scripts/bump_version.py <NEW_VERSION> [OLD_VERSION]

OLD_VERSION 缺省时从 backend/pyproject.toml 读取当前版本。
只替换精确匹配的版本字符串；uv.lock 仅替换本项目包条目
（避免误伤同版本号的第三方依赖，如 pytest-cov 5.0.0）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def replace_in_file(rel: str, replacements: list[tuple[str, str]]) -> None:
    """Replace exact strings in a file; warn instead of writing when no match."""
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    hits = 0
    for old, new in replacements:
        n = text.count(old)
        hits += n
        text = text.replace(old, new)
    if hits == 0:
        print(f"WARN  {rel}: 未找到任何匹配，未修改")
        return
    path.write_text(text, encoding="utf-8")
    print(f"Updated {rel} ({hits} 处)")


def bump_uv_lock(old: str, new: str) -> None:
    """Only bump the project package's own entry in uv.lock."""
    rel = "backend/uv.lock"
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r'(\[\[package\]\]\nname = "talent-platform-backend"\nversion = ")'
        + re.escape(old)
        + '(")'
    )
    new_text, n = pattern.subn(rf"\g<1>{new}\g<2>", text)
    if n == 0:
        print(f"WARN  {rel}: 未找到 talent-platform-backend 的版本条目，未修改")
        return
    path.write_text(new_text, encoding="utf-8")
    print(f"Updated {rel} ({n} 处)")


def read_current_version() -> str:
    text = (ROOT / "backend/pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version = "(\d+\.\d+\.\d+)"', text, re.MULTILINE)
    if not m:
        sys.exit("无法从 backend/pyproject.toml 读取当前版本")
    return m.group(1)


def main() -> None:
    if len(sys.argv) < 2 or len(sys.argv) > 3 or not _VERSION_RE.match(sys.argv[1]):
        sys.exit("用法: python scripts/bump_version.py <NEW_VERSION> [OLD_VERSION]，如 5.2.0")
    new = sys.argv[1]
    old = sys.argv[2] if len(sys.argv) == 3 else read_current_version()
    if not _VERSION_RE.match(old):
        sys.exit(f"OLD_VERSION 格式非法: {old}")
    if old == new:
        sys.exit(f"新旧版本相同（{new}），无需 bump")

    print(f"Bump {old} -> {new}")
    replace_in_file("backend/pyproject.toml", [(f'version = "{old}"', f'version = "{new}"')])
    replace_in_file("frontend/package.json", [(f'"version": "{old}"', f'"version": "{new}"')])
    replace_in_file(
        "backend/app/core/config.py",
        [(f'APP_VERSION: str = "{old}"', f'APP_VERSION: str = "{new}"')],
    )
    bump_uv_lock(old, new)
    replace_in_file("backend/openapi.json", [(f'"version": "{old}"', f'"version": "{new}"')])
    replace_in_file("CLAUDE.md", [(f"V{old}", f"V{new}")])
    replace_in_file("AGENTS.md", [(f"当前版本**：**V{old}**", f"当前版本**：**V{new}**")])
    replace_in_file(
        "README.md",
        [
            (f"智能人才库 V{old}", f"智能人才库 V{new}"),
            (f"当前版本 V{old}", f"当前版本 V{new}"),
        ],
    )
    print("Done.")


if __name__ == "__main__":
    main()
