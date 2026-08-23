"""Genealogy read path - network query around a root talent.

Split from ``genealogy_service.py`` (2026-08 cohesion refactor): that module
keeps the inference/write pipeline (infer / upsert / prune), while this module
owns the BFS read path used by the network endpoint.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.genealogy import GenealogyEdge, TalentInfluenceScore
from app.domains.academic.models.talent import Talent


class GenealogyQueryService:
    """Read-side queries over genealogy edges."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_network(
        self,
        talent_id: int,
        depth: int,
        min_confidence: float,
        relationship_type: str | None,
        tier_filter: str | None,
    ) -> dict[str, Any] | None:
        """Get genealogy network centered on a given talent.

        Returns None if talent not found.
        """
        from app.domains.academic.schemas.genealogy import (
            GenealogyLink,
            GenealogyNode,
            GenealogyStats,
        )

        root_result = await self.session.execute(
            select(Talent).where(Talent.talent_id == talent_id, Talent.is_visible.is_(True))
        )
        root_talent = root_result.scalar_one_or_none()
        if not root_talent:
            return None

        inf_result = await self.session.execute(
            select(TalentInfluenceScore).where(TalentInfluenceScore.talent_id == talent_id)
        )
        root_score = inf_result.scalar_one_or_none()

        # NOTE: avoid root_talent.primary_school_name property which triggers
        # lazy loading in async session (MissingGreenlet). Institution is
        # fetched separately if needed.
        root_node = GenealogyNode(
            talent_id=root_talent.talent_id,
            name=root_talent.name,
            institution=None,
            composite_score=root_score.composite_score if root_score else 0.0,
            tier=root_score.tier if root_score else "tier4",
            h_index=root_talent.h_index or 0,
            cited_by_count=root_talent.cited_by_count or 0,
            is_root=True,
        )

        nodes_map: dict[int, GenealogyNode] = {}
        links: list[GenealogyLink] = []
        visited_pairs: set[tuple[int, int]] = set()

        current_level = {talent_id}
        for _ in range(depth):
            if not current_level:
                break
            next_level: set[int] = set()

            query = select(GenealogyEdge).where(
                GenealogyEdge.from_talent_id.in_(current_level)
                | GenealogyEdge.to_talent_id.in_(current_level)
            )
            if relationship_type:
                query = query.where(GenealogyEdge.relationship_type == relationship_type)
            query = query.where(GenealogyEdge.confidence_score >= min_confidence)

            edge_result = await self.session.execute(query)
            edges = edge_result.scalars().all()

            for edge in edges:
                pair = (edge.from_talent_id, edge.to_talent_id)
                if pair in visited_pairs:
                    continue
                visited_pairs.add(pair)

                links.append(
                    GenealogyLink(
                        source=edge.from_talent_id,
                        target=edge.to_talent_id,
                        type=edge.relationship_type,
                        confidence=edge.confidence_score,
                        shared_institution=edge.shared_institution,
                        evidence_count=edge.evidence_count,
                        first_year=edge.first_year,
                        last_year=edge.last_year,
                    )
                )

                next_level.add(edge.from_talent_id)
                next_level.add(edge.to_talent_id)

            current_level = next_level - {talent_id}

        all_tids = {link.source for link in links} | {link.target for link in links}
        all_tids.discard(talent_id)

        if all_tids:
            MAX_PARAMS = 30000
            tids_list = list(all_tids)

            talent_info: dict[int, Any] = {}
            for i in range(0, len(tids_list), MAX_PARAMS):
                batch = tids_list[i : i + MAX_PARAMS]
                talent_result = await self.session.execute(
                    select(
                        Talent.talent_id, Talent.name, Talent.h_index, Talent.cited_by_count
                    ).where(Talent.talent_id.in_(batch))
                )
                for row in talent_result.mappings().all():
                    talent_info[row.talent_id] = row

            score_map: dict[int, Any] = {}
            for i in range(0, len(tids_list), MAX_PARAMS):
                batch = tids_list[i : i + MAX_PARAMS]
                score_result = await self.session.execute(
                    select(TalentInfluenceScore).where(TalentInfluenceScore.talent_id.in_(batch))
                )
                for s in score_result.scalars().all():
                    score_map[s.talent_id] = s

            for tid in all_tids:
                t_info = talent_info.get(tid)
                s_info = score_map.get(tid)
                if not t_info:
                    continue
                if tier_filter and (not s_info or s_info.tier != tier_filter):
                    continue
                nodes_map[tid] = GenealogyNode(
                    talent_id=tid,
                    name=t_info.name,
                    institution=None,
                    composite_score=s_info.composite_score if s_info else 0.0,
                    tier=s_info.tier if s_info else "tier4",
                    h_index=t_info.h_index or 0,
                    cited_by_count=t_info.cited_by_count or 0,
                    is_root=False,
                )

        valid_tids = set(nodes_map.keys()) | {talent_id}
        filtered_links = [
            link for link in links if link.source in valid_tids and link.target in valid_tids
        ]
        nodes = list(nodes_map.values())

        tier_dist: dict[str, int] = {}
        for n in nodes:
            tier_dist[n.tier] = tier_dist.get(n.tier, 0) + 1
        tier_dist[root_node.tier] = tier_dist.get(root_node.tier, 0) + 1

        return {
            "root_talent": root_node,
            "nodes": nodes,
            "links": filtered_links,
            "stats": GenealogyStats(
                total_nodes=len(nodes) + 1,
                total_links=len(filtered_links),
                tier_distribution=tier_dist,
            ),
        }
