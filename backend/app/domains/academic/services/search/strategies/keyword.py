"""Keyword search strategy (ILIKE pattern matching)."""

from __future__ import annotations

import logging

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.talent import Talent
from app.domains.academic.repositories.talent_repository import TalentRepository
from app.domains.academic.services.search.strategies.base import SearchStrategy
from app.domains.academic.services.search.utils import apply_talent_filters, talent_to_dict

logger = logging.getLogger(__name__)


class KeywordSearchStrategy(SearchStrategy):
    """Keyword search using ILIKE pattern matching with GIN index support."""

    async def search(
        self,
        query: str,
        page: int,
        page_size: int,
        filters: dict | None,
        fields: list[str] | None = None,
        fuzzy: bool = False,
        session: AsyncSession | None = None,
    ) -> dict:
        session = session or self.context.session
        repo = (
            self.context.talent_repo
            if session is self.context.session
            else TalentRepository(session)
        )

        # Default search fields
        if fields is None:
            fields = ["name", "title", "topics", "works"]

        matched_talent_ids: set = set()
        pattern = f"%{query}%"

        # 1. Name and title search (using ILIKE)
        basic_fields = [f for f in fields if f in ["name", "title"]]
        if basic_fields:
            query_stmt = select(Talent.talent_id).where(Talent.is_visible.is_(True))

            field_mapping = {
                "name": [Talent.name, Talent.name_en],
                "title": [Talent.current_title],
            }

            search_conditions = []
            for field in basic_fields:
                for col in field_mapping.get(field, []):
                    if col is not None:
                        search_conditions.append(col.ilike(pattern))

            if search_conditions:
                query_stmt = query_stmt.where(or_(*search_conditions))
                query_stmt = apply_talent_filters(query_stmt, filters)
                result = await session.execute(query_stmt)
                for row in result.fetchall():
                    matched_talent_ids.add(row.talent_id)

        # 2. Research topics search (fuzzy match for openalex_topics)
        if "topics" in fields:
            query_stmt = (
                select(Talent.talent_id)
                .where(Talent.is_visible.is_(True))
                .where(
                    text("core_talent.openalex_topics::text ILIKE :pattern").bindparams(
                        pattern=pattern
                    )
                )
            )
            query_stmt = apply_talent_filters(query_stmt, filters)
            result = await session.execute(query_stmt)
            for row in result.fetchall():
                matched_talent_ids.add(row.talent_id)

        # 3. Paper title search (using pg_trgm GIN index)
        if "works" in fields:
            try:
                work_talents = await repo._search_by_paper_titles_gin(
                    keywords=[query],
                    filters=filters,
                    limit=page_size * 3,
                )
                for t in work_talents:
                    matched_talent_ids.add(t.talent_id)
            except Exception as e:
                logger.warning(f"Paper title GIN search failed: {e}")

        # 4. Return empty if no matches
        if not matched_talent_ids:
            return {"total": 0, "items": []}

        # 5. Get full talent data and sort
        talent_ids_list = list(matched_talent_ids)
        talents = await repo.get_by_ids(talent_ids_list, include_relations=True)
        talents.sort(key=lambda t: t.cited_by_count or 0, reverse=True)

        # 6. Calculate total and paginate
        total = len(talents)
        offset = (page - 1) * page_size
        paginated_talents = talents[offset : offset + page_size]

        # 7. Convert results
        items = [talent_to_dict(t) for t in paginated_talents]

        return {"total": total, "items": items}
