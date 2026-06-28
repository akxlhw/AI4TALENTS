"""Data access layer for lab_web_site tables (v2)."""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab_web.constants.normalizers import normalize_name
from app.domains.lab_web.models.lab_web import LWLabRegistry, LWRawPerson
from app.domains.lab_web.models.lab_web_site import LWSiteConfig, LWSiteRawPage


class LWSiteRepository:
    """Read/write access to lw_site_config and lw_site_raw_page."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ===== Sites =====

    async def get_site_by_code(self, site_code: str) -> LWSiteConfig | None:
        stmt = select(LWSiteConfig).where(LWSiteConfig.site_code == site_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sites(self, only_active: bool = False) -> list[LWSiteConfig]:
        stmt = select(LWSiteConfig)
        if only_active:
            stmt = stmt.where(LWSiteConfig.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_site_collected_at(self, site_code: str, collected_at: Any) -> None:
        site = await self.get_site_by_code(site_code)
        if site:
            site.last_collected_at = collected_at
            await self.session.commit()

    async def resolve_lab_id(self, parent_lab_code: str) -> int:
        """Resolve parent_lab_code -> lw_lab_registry.lab_id (for FK compliance).

        lw_raw_person.lab_id has a FK to lw_lab_registry.lab_id, so v2 (which
        reuses lw_raw_person) must supply a real lab_id rather than a sentinel.
        Public so the orchestration service can resolve a task's lab_id without
        reaching into repository internals.
        """
        stmt = select(LWLabRegistry.lab_id).where(LWLabRegistry.lab_code == parent_lab_code)
        result = await self.session.execute(stmt)
        lab_id = result.scalar_one_or_none()
        if lab_id is None:
            raise ValueError(
                f"parent_lab_code {parent_lab_code!r} not found in lw_lab_registry; "
                "cannot insert lw_raw_person without a valid lab_id FK"
            )
        return int(lab_id)

    # ===== Raw page cache =====

    async def find_cached_page(self, site_code: str, html_hash: str) -> LWSiteRawPage | None:
        """Return a parsed cached page for (site_code, html_hash), or None.

        Cache hits ONLY when parse_status='parsed' (needs_review/failed/pending
        are cache misses and must be re-parsed).
        """
        stmt = select(LWSiteRawPage).where(
            LWSiteRawPage.site_code == site_code,
            LWSiteRawPage.html_hash == html_hash,
            LWSiteRawPage.parse_status == "parsed",
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def insert_raw_page(
        self,
        site_code: str,
        people_url: str,
        html_content: str,
        html_hash: str,
        parsed_persons: list[dict] | None = None,
        parse_status: str = "pending",
        parse_error: str | None = None,
        llm_model: str | None = None,
        llm_tokens_used: int | None = None,
    ) -> LWSiteRawPage:
        row = LWSiteRawPage(
            site_code=site_code,
            people_url=people_url,
            html_content=html_content,
            html_hash=html_hash,
            parsed_persons=parsed_persons,
            parse_status=parse_status,
            parse_error=parse_error,
            llm_model=llm_model,
            llm_tokens_used=llm_tokens_used,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    # ===== Raw persons =====

    async def upsert_site_raw_persons(
        self,
        site_code: str,
        parent_lab_code: str,
        parsed_persons: list[dict],
        task_id: int,
    ) -> list[LWRawPerson]:
        """Convert LLM-parsed persons to lw_raw_person rows.

        Dedups within this batch by content_hash. raw layer is append-only.
        """
        lab_id = await self.resolve_lab_id(parent_lab_code)
        seen: set[str] = set()
        created: list[LWRawPerson] = []
        for p in parsed_persons:
            name = normalize_name(p.get("name")) or p.get("name")
            role_section = p.get("role_section") or "Unknown"
            homepage = p.get("homepage")
            department = p.get("department")
            hash_ = hashlib.sha256(
                f"{site_code}|{name}|{role_section}|{homepage or ''}".encode()
            ).hexdigest()
            if hash_ in seen:
                continue
            seen.add(hash_)
            row = LWRawPerson(
                lab_id=lab_id,
                source_url=None,
                name_raw=p.get("name"),
                title_raw=None,  # lab-site has role_section, not a job title
                email_raw=None,
                homepage_url=homepage,
                avatar_url=None,
                raw_data={
                    "site_code": site_code,
                    "parent_lab_code": parent_lab_code,
                    "role_section": role_section,
                    "department": department,
                    "homepage": homepage,
                    "source_type": "lab_web_site",
                },
                collect_task_id=task_id,
                content_hash=hash_,
            )
            self.session.add(row)
            created.append(row)
        await self.session.commit()
        return created

    async def get_raw_persons_by_task(self, task_id: int) -> list[LWRawPerson]:
        stmt = select(LWRawPerson).where(LWRawPerson.collect_task_id == task_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
