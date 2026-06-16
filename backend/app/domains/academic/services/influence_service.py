"""Influence score computation service for academic talents.

Computes composite influence scores based on h-index, citations, works,
collaboration degree, and bridge centrality (degree-based approximation v1).
"""

from __future__ import annotations

import logging
import math
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.collaboration import Collaboration
from app.domains.academic.models.genealogy import TalentInfluenceScore
from app.domains.academic.models.talent import Talent

logger = logging.getLogger(__name__)

# Weights for composite score
W_H_INDEX = 0.30
W_CITATION = 0.25
W_WORKS = 0.15
W_COLLAB = 0.15
W_BRIDGE = 0.15

# Tier thresholds
TIER_THRESHOLDS = [
    (85.0, "tier1"),
    (60.0, "tier2"),
    (40.0, "tier3"),
]


class InfluenceService:
    """Service for computing and managing talent influence scores."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def compute_all_scores(self) -> dict[str, int]:
        """Compute influence scores for all visible talents.

        Returns:
            dict with counts of processed talents per tier.
        """
        logger.info("Starting influence score computation")

        # Step 1: Fetch all visible talents with metrics
        result = await self.session.execute(
            select(
                Talent.talent_id,
                Talent.h_index,
                Talent.cited_by_count,
                Talent.works_count,
            ).where(Talent.is_visible.is_(True))
        )
        talents = result.all()
        if not talents:
            logger.warning("No visible talents found for influence scoring")
            return {"total": 0, "tier1": 0, "tier2": 0, "tier3": 0, "tier4": 0}

        talent_ids = [t[0] for t in talents]

        # Step 2: Compute collaboration counts
        collab_counts = await self._get_collaboration_counts(talent_ids)

        # Step 3: Compute bridge scores (degree centrality approximation)
        bridge_scores = await self._compute_bridge_scores(talent_ids)

        # Step 4: Normalize metrics
        h_indices = [t[1] or 0 for t in talents]
        citations = [t[2] or 0 for t in talents]
        works = [t[3] or 0 for t in talents]
        collabs = [collab_counts.get(t[0], 0) for t in talents]
        bridges = [bridge_scores.get(t[0], 0) for t in talents]

        h_norm_map = self._percentile_normalize(
            {t[0]: v for t, v in zip(talents, h_indices, strict=False)}
        )
        citation_norm_map = self._log_normalize(
            {t[0]: v for t, v in zip(talents, citations, strict=False)}
        )
        works_norm_map = self._log_normalize(
            {t[0]: v for t, v in zip(talents, works, strict=False)}
        )
        collab_norm_map = self._percentile_normalize(
            {t[0]: v for t, v in zip(talents, collabs, strict=False)}
        )
        bridge_norm_map = self._percentile_normalize(
            {t[0]: v for t, v in zip(talents, bridges, strict=False)}
        )

        # Step 5: Build score objects and upsert
        tier_counts: dict[str, int] = {"tier1": 0, "tier2": 0, "tier3": 0, "tier4": 0}
        scores_to_upsert: list[dict[str, Any]] = []

        for talent in talents:
            tid = talent[0]
            h_n = h_norm_map.get(tid, 0.0)
            c_n = citation_norm_map.get(tid, 0.0)
            w_n = works_norm_map.get(tid, 0.0)
            col_n = collab_norm_map.get(tid, 0.0)
            b_n = bridge_norm_map.get(tid, 0.0)

            composite = (
                W_H_INDEX * h_n
                + W_CITATION * c_n
                + W_WORKS * w_n
                + W_COLLAB * col_n
                + W_BRIDGE * b_n
            )

            tier = "tier4"
            for threshold, t_name in TIER_THRESHOLDS:
                if composite >= threshold:
                    tier = t_name
                    break

            tier_counts[tier] = tier_counts.get(tier, 0) + 1

            scores_to_upsert.append(
                {
                    "talent_id": tid,
                    "h_index_score": round(h_n, 2),
                    "citation_score": round(c_n, 2),
                    "works_score": round(w_n, 2),
                    "collaboration_score": round(col_n, 2),
                    "bridge_score": round(b_n, 2),
                    "composite_score": round(composite, 2),
                    "tier": tier,
                    "is_root": tier == "tier1",
                }
            )

        # Batch upsert
        await self._bulk_upsert_scores(scores_to_upsert)

        await self.session.commit()
        logger.info(
            f"Influence scoring completed: {len(scores_to_upsert)} talents, "
            f"tier distribution: {tier_counts}"
        )
        tier_counts["total"] = len(scores_to_upsert)
        return tier_counts

    async def _get_collaboration_counts(self, talent_ids: list[int]) -> dict[int, int]:
        """Get collaboration count per talent from core_collaboration.

        Batched to avoid asyncpg's 32767 parameter limit.
        """
        if not talent_ids:
            return {}

        MAX_PARAMS = 30000
        counts: dict[int, int] = {}

        for i in range(0, len(talent_ids), MAX_PARAMS):
            batch = talent_ids[i : i + MAX_PARAMS]

            result = await self.session.execute(
                select(
                    Collaboration.talent_id_1.label("tid"),
                    func.count().label("cnt"),
                )
                .where(Collaboration.talent_id_1.in_(batch))
                .group_by(Collaboration.talent_id_1)
            )
            for row in result.mappings().all():
                counts[row.tid] = counts.get(row.tid, 0) + row.cnt

            result2 = await self.session.execute(
                select(
                    Collaboration.talent_id_2.label("tid"),
                    func.count().label("cnt"),
                )
                .where(Collaboration.talent_id_2.in_(batch))
                .group_by(Collaboration.talent_id_2)
            )
            for row in result2.mappings().all():
                counts[row.tid] = counts.get(row.tid, 0) + row.cnt

        return counts

    async def _compute_bridge_scores(self, talent_ids: list[int]) -> dict[int, int]:
        """Compute bridge score as degree centrality (collaboration count).

        v1 approximation: use collaboration count as proxy for betweenness.
        Future: switch to actual betweenness centrality via NetworkX.
        """
        return await self._get_collaboration_counts(talent_ids)

    @staticmethod
    def _percentile_normalize(values: dict[int, float | int]) -> dict[int, float]:
        """Normalize values to 0-100 using percentile ranking."""
        if not values:
            return {}
        sorted_items = sorted(values.items(), key=lambda x: x[1])
        n = len(sorted_items)
        result: dict[int, float] = {}
        for rank, (tid, _val) in enumerate(sorted_items):
            # percentile rank: (rank / (n-1)) * 100
            if n == 1:
                result[tid] = 50.0
            else:
                result[tid] = (rank / (n - 1)) * 100.0
        return result

    @staticmethod
    def _log_normalize(values: dict[int, float | int]) -> dict[int, float]:
        """Normalize values using log scaling to 0-100."""
        if not values:
            return {}
        max_val = max(values.values())
        if max_val <= 0:
            return {tid: 0.0 for tid in values}
        log_max = math.log(max_val + 1)
        return {tid: (math.log(v + 1) / log_max) * 100.0 for tid, v in values.items()}

    async def _bulk_upsert_scores(self, scores: list[dict[str, Any]]) -> None:
        """Bulk upsert influence scores.

        Batched to avoid asyncpg's 32767 parameter limit.
        Each row has ~11 parameters, so batch size of 2000 is safe.
        """
        if not scores:
            return

        from sqlalchemy.dialects.postgresql import insert

        BATCH_SIZE = 2000
        for i in range(0, len(scores), BATCH_SIZE):
            batch = scores[i : i + BATCH_SIZE]
            stmt = insert(TalentInfluenceScore).values(batch)
            update_dict = {
                "h_index_score": stmt.excluded.h_index_score,
                "citation_score": stmt.excluded.citation_score,
                "works_score": stmt.excluded.works_score,
                "collaboration_score": stmt.excluded.collaboration_score,
                "bridge_score": stmt.excluded.bridge_score,
                "composite_score": stmt.excluded.composite_score,
                "tier": stmt.excluded.tier,
                "is_root": stmt.excluded.is_root,
                "computed_at": func.now(),
            }
            await self.session.execute(
                stmt.on_conflict_do_update(
                    index_elements=["talent_id"],
                    set_=update_dict,
                )
            )
        await self.session.flush()

    async def get_ranking(self, tier: str | None, limit: int) -> list[dict[str, Any]]:
        """Get influence ranking list."""
        from app.domains.academic.models.genealogy import TalentInfluenceScore
        from app.domains.academic.schemas.genealogy import InfluenceRankingItem

        query = (
            select(
                Talent.talent_id,
                Talent.name,
                Talent.h_index,
                Talent.cited_by_count,
                Talent.works_count,
                TalentInfluenceScore.composite_score,
                TalentInfluenceScore.tier,
            )
            .join(TalentInfluenceScore, Talent.talent_id == TalentInfluenceScore.talent_id)
            .where(Talent.is_visible.is_(True))
            .order_by(TalentInfluenceScore.composite_score.desc())
        )
        if tier:
            query = query.where(TalentInfluenceScore.tier == tier)

        result = await self.session.execute(query.limit(limit))
        rows = result.mappings().all()

        return [
            InfluenceRankingItem(
                talent_id=row.talent_id,
                name=row.name,
                composite_score=row.composite_score or 0.0,
                tier=row.tier or "tier4",
                h_index=row.h_index or 0,
                cited_by_count=row.cited_by_count or 0,
                works_count=row.works_count or 0,
            ).model_dump()
            for row in rows
        ]
