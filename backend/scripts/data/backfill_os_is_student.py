"""Backfill os_developer.is_student for all existing developers.

Recomputes the student flag with ``os_student_classifier`` for every row in
``os_developer`` and prints hit statistics.

Usage:
    cd backend && uv run python -X utf8 scripts/data/backfill_os_is_student.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.domains.open_source.models.open_source import OSDeveloper
from app.domains.open_source.services.os_student_classifier import classify, has_staff_keyword

# GBK 控制台下 SQLAlchemy echo 日志可能含无法编码的字符，直接屏蔽
logging.getLogger("sqlalchemy.engine").setLevel(logging.CRITICAL)


async def main() -> None:
    stats = {
        "total": 0,
        "bio_student": 0,
        "company_school": 0,
        "staff_excluded": 0,
        "marked": 0,
        "changed": 0,
    }

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(OSDeveloper))
        developers = list(result.scalars().all())

        from app.domains.open_source.services.os_student_classifier import has_staff_keyword

        for dev in developers:
            stats["total"] += 1
            # staff 排除统计：bio 命中教职工关键词而未被标记的人数
            res = classify(company=dev.company, bio=dev.bio, email=dev.email)
            if res.is_student:
                stats[res.reason] += 1
                stats["marked"] += 1
            elif has_staff_keyword(dev.bio):
                stats["staff_excluded"] += 1
            if res.is_student != bool(dev.is_student):
                dev.is_student = res.is_student
                stats["changed"] += 1

        await session.commit()

    print("Backfill os_developer.is_student finished:")
    print(f"  total developers : {stats['total']}")
    print(f"  bio_student hits : {stats['bio_student']}")
    print(f"  company_school   : {stats['company_school']}")
    print(f"  staff excluded   : {stats['staff_excluded']}")
    print(f"  marked is_student: {stats['marked']}")
    print(f"  rows changed     : {stats['changed']}")


if __name__ == "__main__":
    asyncio.run(main())
