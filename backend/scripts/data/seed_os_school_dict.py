"""Export school dictionary for open-source student detection.

Reads the academic domain's core_school / core_school_alias tables from the
development database and writes all school names and aliases to
``app/domains/open_source/constants/school_dict.json`` (loaded at runtime by
``os_student_classifier``). Standalone script — cross-domain import rules do
not apply under ``scripts/``.

Usage:
    cd backend && uv run python -X utf8 scripts/data/seed_os_school_dict.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select

import app.model_registry  # noqa: F401 - 注册全部模型，解析 School 的 relationship
from app.core.database import AsyncSessionLocal
from app.domains.academic.models.school import School, SchoolAlias

OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "app/domains/open_source/constants/school_dict.json"
)

# GBK 控制台下 SQLAlchemy echo 日志可能含无法编码的字符，直接屏蔽
logging.getLogger("sqlalchemy.engine").setLevel(logging.CRITICAL)


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(School.school_name, School.school_alias).where(School.is_visible.is_(True))
        )
        names: set[str] = set()
        aliases: dict[str, str] = {}
        for school_name, school_alias in result.all():
            if school_name:
                names.add(school_name)
            if school_alias:
                aliases[school_alias] = school_name

        alias_result = await session.execute(
            select(SchoolAlias.alias_name, School.school_name).join(
                School, SchoolAlias.school_id == School.school_id
            )
        )
        for alias_name, school_name in alias_result.all():
            if alias_name:
                aliases[alias_name] = school_name

    payload = {
        "names": sorted(names),
        "aliases": dict(sorted(aliases.items())),
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Wrote {OUTPUT_PATH}")
    print(f"  names: {len(names)}, aliases: {len(aliases)}")


if __name__ == "__main__":
    asyncio.run(main())
