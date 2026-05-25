#!/usr/bin/env python3
"""Bump version number across all project files."""

OLD_VERSION = "2.0.4"
NEW_VERSION = "2.1.0"


def replace_in_file(path: str, replacements: list[tuple[str, str]]) -> None:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    for old, new in replacements:
        text = text.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Updated {path}")


def main() -> None:
    replace_in_file("backend/pyproject.toml", [(f'version = "{OLD_VERSION}"', f'version = "{NEW_VERSION}"')])
    replace_in_file("frontend/package.json", [(f'"version": "{OLD_VERSION}"', f'"version": "{NEW_VERSION}"')])
    replace_in_file("backend/app/core/config.py", [(f'APP_VERSION: str = "{OLD_VERSION}"', f'APP_VERSION: str = "{NEW_VERSION}"')])
    replace_in_file("backend/uv.lock", [(f'version = "{OLD_VERSION}"', f'version = "{NEW_VERSION}"')])
    replace_in_file("backend/openapi.json", [(f'"version": "{OLD_VERSION}"', f'"version": "{NEW_VERSION}"')])
    replace_in_file("CLAUDE.md", [(f"V{OLD_VERSION}", f"V{NEW_VERSION}")])
    replace_in_file(
        "README.md",
        [
            (f"智能人才库 V{OLD_VERSION}", f"智能人才库 V{NEW_VERSION}"),
            (f"当前版本 V{OLD_VERSION}", f"当前版本 V{NEW_VERSION}"),
        ],
    )
    print("Done.")


if __name__ == "__main__":
    main()
