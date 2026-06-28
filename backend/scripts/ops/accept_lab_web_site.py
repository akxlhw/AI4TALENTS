"""Acceptance script for lab_web_site v2 验收标准 §8 (real LLM, manual/slow).

Runs a REAL LLM parse against the Stanford NLP Group People page and reports
the extracted persons + role accuracy for human review. This is the one v2
verification step that cannot run in CI (requires a real LLM API key + network).

Usage:
    # 1. Configure backend/.env:
    #    LLM_ENABLED=true
    #    LLM_API_KEY=<your DeepSeek / OpenAI / Zhipu key>
    #    LLM_API_BASE=https://api.deepseek.com/v1   (or your provider)
    #    LLM_MODEL=deepseek-chat                     (or your model)
    # 2. Run:
    cd backend && uv run python scripts/ops/accept_lab_web_site.py
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Add backend/ to sys.path so `app` is importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Register all mappers (avoid the SQLAlchemy partial-import trap documented in AGENTS.md).
import app.model_registry  # noqa: F401,E402

from sqlalchemy import func, select
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.domains.academic.models.talent import Talent
from app.domains.lab_web.models.lab_web_site import LWSiteConfig, LWSiteRawPage
from app.domains.lab_web.repositories.lab_web.site import LWSiteRepository
from app.domains.lab_web.services.collectors.base_site_collector import (
    BaseLabSiteCollector,
    SiteCollectContext,
)
from app.domains.lab_web.services.collectors.scrapling_fetcher import ScraplingFetcher
from app.domains.lab_web.services.lw_site_person_service import LWSitePersonService
from app.domains.shared.models.enums import RoleType, SourceType
from app.domains.shared.services.llm.llm_gateway import create_llm_gateway

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("accept")


async def main() -> int:
    if not settings.LLM_ENABLED or not getattr(settings, "LLM_API_KEY", ""):
        print("ERROR: LLM not configured. Set LLM_ENABLED=true and LLM_API_KEY in backend/.env.")
        return 2

    async with AsyncSessionLocal() as session:
        repo = LWSiteRepository(session)
        person_svc = LWSitePersonService(session)
        site = await repo.get_site_by_code("stanford_nlp_group")
        if site is None:
            print("ERROR: stanford_nlp_group not seeded. Run: alembic upgrade head")
            return 3

        print(f"=== Real LLM acceptance: {site.site_code} ===")
        print(f"  people_url: {site.people_url}")
        print(f"  llm model:  {settings.LLM_MODEL} @ {settings.LLM_API_BASE}")

        fetcher = ScraplingFetcher(fetch_mode="static")
        llm = create_llm_gateway()
        collector = BaseLabSiteCollector(
            fetcher=fetcher, site=site, repo=repo, person_service=person_svc, llm_gateway=llm
        )
        ctx = SiteCollectContext(task_id=0, site_code="stanford_nlp_group", force_reparse=True)
        try:
            await collector.collect(ctx)
        except Exception as exc:
            print(f"FAIL: collection raised {type(exc).__name__}: {exc}")
            return 1

        # Report results
        latest = (
            await session.execute(
                select(LWSiteRawPage)
                .where(LWSiteRawPage.site_code == "stanford_nlp_group")
                .order_by(LWSiteRawPage.created_at.desc())
                .limit(1)
            )
        ).scalar_one()
        print()
        print(f"=== RAW PAGE ===")
        print(f"  parse_status:    {latest.parse_status}")
        print(f"  html bytes:      {len(latest.html_content)}")
        print(f"  llm_model:       {latest.llm_model}")
        print(f"  llm_tokens_used: {latest.llm_tokens_used}")
        if latest.parse_error:
            print(f"  parse_error:     {latest.parse_error[:200]}")

        talents = (
            await session.execute(
                select(Talent).where(Talent.source_type == SourceType.LAB_WEB_SITE.value)
            )
        ).scalars().all()
        print()
        print(f"=== CORE_TALENT (lab_web_site): {len(talents)} persons ===")
        # Role distribution
        role_counts: dict[str, int] = {}
        for t in talents:
            role_counts[t.role_type] = role_counts.get(t.role_type, 0) + 1
        print(f"  role distribution: {role_counts}")
        print(f"  --- first 10 ---")
        for t in talents[:10]:
            section = (t.extra_data or {}).get("role_section_raw", "?")
            print(f"    {t.name:24} role_type={t.role_type:16} section={section}")

        # Verdict
        if latest.parse_status != "parsed":
            print()
            print(f"RESULT: needs_review / partial — LLM did not parse cleanly.")
            print("        Inspect the LLM output and tune the prompt if accuracy is poor.")
            return 1
        if not talents:
            print("RESULT: FAIL — parsed but 0 persons synced to core_talent.")
            return 1
        print()
        print(f"RESULT: SUCCESS — {len(talents)} persons parsed and synced with roles.")
        print("        Manually verify a few names/roles against https://nlp.stanford.edu/people/")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
