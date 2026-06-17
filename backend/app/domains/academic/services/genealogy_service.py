"""Genealogy inference service: extract advisor-student relationships from RawWork.

Uses last-author + first-author positional heuristics on authorships from
OpenAlex raw_json, with confidence scoring based on co-authorship patterns.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.genealogy import GenealogyEdge
from app.domains.academic.models.raw_data import RawWork
from app.domains.academic.models.standardized import StdAuthor
from app.domains.academic.models.talent import Talent

logger = logging.getLogger(__name__)

# Confidence scoring constants
SCORE_POSITION_PATTERN = 0.30
SCORE_SHARED_INSTITUTION = 0.15
SCORE_MULTIPLE_PAPERS = 0.20  # max bonus for >= 7 papers
SCORE_TIME_SPAN = 0.10
SCORE_ROLE_DIFF = 0.15

MIN_CONFIDENCE = 0.30
PAPER_COUNT_BONUS_START = 3
PAPER_COUNT_BONUS_PER_PAPER = 0.05
PAPER_COUNT_BONUS_MAX = 0.20
TIME_SPAN_YEARS = 3

BATCH_SIZE = 500


class GenealogyService:
    """Service for inferring and managing academic genealogy edges."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def infer_all_genealogy(
        self, progress_callback: callable | None = None
    ) -> dict[str, int]:
        """Infer genealogy edges from all RawWork records.

        Returns:
            dict with counts: total_raw_works, edges_inferred, edges_upserted
        """
        logger.info("Starting genealogy inference from RawWork")

        # Count total raw works
        count_result = await self.session.execute(select(func.count()).select_from(RawWork))
        total_works = count_result.scalar_one()
        if total_works == 0:
            logger.warning("No RawWork records found")
            return {"total_raw_works": 0, "edges_inferred": 0, "edges_upserted": 0}

        # Build openalex_author_id -> talent_id mapping
        talent_map = await self._build_talent_map()
        if not talent_map:
            logger.warning("No talent mapping available for genealogy inference")
            return {"total_raw_works": total_works, "edges_inferred": 0, "edges_upserted": 0}

        # Accumulators for pair-level stats
        pair_stats: dict[tuple[int, int], dict[str, Any]] = defaultdict(
            lambda: {
                "paper_count": 0,
                "shared_institution_count": 0,
                "years": set(),
                "work_ids": [],
                "from_role": None,
                "to_role": None,
            }
        )

        processed = 0
        last_work_id = 0
        works_with_pairs = 0

        # Keyset pagination to avoid missing rows when RawWork is concurrently modified
        while True:
            result = await self.session.execute(
                select(RawWork.raw_work_id, RawWork.raw_json, RawWork.openalex_work_id)
                .where(RawWork.raw_work_id > last_work_id)
                .order_by(RawWork.raw_work_id)
                .limit(BATCH_SIZE)
            )
            rows = result.all()
            if not rows:
                break

            batch_pairs_before = len(pair_stats)
            for _raw_work_id, raw_json, openalex_work_id in rows:
                self._process_single_work(raw_json, openalex_work_id, talent_map, pair_stats)
            if len(pair_stats) > batch_pairs_before:
                works_with_pairs += 1

            processed += len(rows)
            last_work_id = rows[-1][0]
            if progress_callback:
                progress_callback(processed, total_works, len(pair_stats))

        logger.info(
            f"Processed {processed} works, {works_with_pairs} contributed pairs, total candidates: {len(pair_stats)}"
        )

        # Compute final confidence and build edges
        edges = self._build_edges_from_stats(pair_stats)
        logger.info(f"Edges after confidence filtering (>= {MIN_CONFIDENCE}): {len(edges)}")

        if edges:
            await self._bulk_upsert_edges(edges)
            logger.info(f"Upserted {len(edges)} edges")
        else:
            logger.info("No edges to upsert")

        # Delete edges below min confidence or not in current batch
        await self._prune_stale_edges(edges)

        await self.session.commit()
        logger.info(f"Genealogy inference complete: {len(edges)} edges upserted")
        return {
            "total_raw_works": total_works,
            "edges_inferred": len(pair_stats),
            "edges_upserted": len(edges),
        }

    async def _build_talent_map(self) -> dict[str, int]:
        """Build mapping from openalex_author_id -> talent_id via StdAuthor."""
        result = await self.session.execute(
            select(StdAuthor.openalex_author_id, Talent.talent_id)
            .join(Talent, StdAuthor.std_author_id == Talent.std_author_id)
            .where(Talent.is_visible.is_(True))
        )
        rows = result.mappings().all()
        logger.debug(f"Talent map join returned {len(rows)} rows")
        return {row.openalex_author_id: row.talent_id for row in rows}

    def _process_single_work(
        self,
        raw_json: str,
        openalex_work_id: str,
        talent_map: dict[str, int],
        pair_stats: dict[tuple[int, int], dict[str, Any]],
    ) -> None:
        """Extract last-author + first-author pairs from a single work."""
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            return

        authorships = data.get("authorships", [])
        if len(authorships) < 2:
            return

        pub_year = data.get("publication_year")

        # Find last author and first author
        last_authors = []
        first_authors = []
        all_institutions: dict[str, set[str]] = {}

        for auth in authorships:
            author = auth.get("author", {})
            author_id = author.get("id", "")
            if not author_id:
                continue
            short_id = author_id.split("/")[-1]

            position = auth.get("author_position", "")
            insts = auth.get("institutions", [])
            inst_ids = {i.get("id", "") for i in insts if i.get("id")}
            if short_id:
                all_institutions[short_id] = inst_ids

            if position == "last":
                last_authors.append(short_id)
            elif position == "first":
                first_authors.append(short_id)

        if not last_authors or not first_authors:
            return

        for last_id in last_authors:
            from_tid = talent_map.get(last_id)
            if from_tid is None:
                continue
            for first_id in first_authors:
                to_tid = talent_map.get(first_id)
                if to_tid is None or from_tid == to_tid:
                    continue

                pair = (from_tid, to_tid)
                stats = pair_stats[pair]
                stats["paper_count"] += 1
                if pub_year:
                    stats["years"].add(pub_year)
                if openalex_work_id:
                    stats["work_ids"].append(openalex_work_id)

                # Check shared institution on this paper
                last_inst = all_institutions.get(last_id, set())
                first_inst = all_institutions.get(first_id, set())
                if last_inst and first_inst and last_inst.intersection(first_inst):
                    stats["shared_institution_count"] += 1

    def _build_edges_from_stats(
        self, pair_stats: dict[tuple[int, int], dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Compute confidence and relationship type for each candidate pair."""
        edges: list[dict[str, Any]] = []

        for (from_tid, to_tid), stats in pair_stats.items():
            paper_count = stats["paper_count"]
            shared_count = stats["shared_institution_count"]
            years = sorted(stats["years"]) if stats["years"] else []
            work_ids = list(set(stats["work_ids"]))[:50]  # cap evidence

            confidence = 0.0
            confidence += SCORE_POSITION_PATTERN

            if shared_count > 0:
                confidence += SCORE_SHARED_INSTITUTION

            # Multiple papers bonus
            if paper_count >= PAPER_COUNT_BONUS_START:
                bonus = min(
                    PAPER_COUNT_BONUS_MAX,
                    (paper_count - PAPER_COUNT_BONUS_START + 1) * PAPER_COUNT_BONUS_PER_PAPER,
                )
                confidence += bonus

            # Time span bonus
            if len(years) >= 2 and (years[-1] - years[0]) >= TIME_SPAN_YEARS:
                confidence += SCORE_TIME_SPAN

            if confidence < MIN_CONFIDENCE:
                continue

            # Determine relationship type
            if confidence >= 0.65 and shared_count > 0:
                rel_type = "mentor_mentee"
            elif confidence >= 0.65:
                rel_type = "advisor_student"
            else:
                rel_type = "senior_junior"

            edges.append(
                {
                    "from_talent_id": from_tid,
                    "to_talent_id": to_tid,
                    "relationship_type": rel_type,
                    "confidence_score": round(min(confidence, 0.99), 2),
                    "evidence_count": paper_count,
                    "shared_institution": shared_count > 0,
                    "first_year": years[0] if years else None,
                    "last_year": years[-1] if years else None,
                    "source_work_ids": work_ids,
                }
            )

        return edges

    async def _bulk_upsert_edges(self, edges: list[dict[str, Any]]) -> None:
        """Bulk upsert genealogy edges.

        Batched to avoid asyncpg's 32767 parameter limit.
        """
        if not edges:
            return

        from sqlalchemy.dialects.postgresql import insert

        BATCH_SIZE = 2000
        for i in range(0, len(edges), BATCH_SIZE):
            batch = edges[i : i + BATCH_SIZE]
            stmt = insert(GenealogyEdge).values(batch)
            update_dict = {
                "relationship_type": stmt.excluded.relationship_type,
                "confidence_score": stmt.excluded.confidence_score,
                "evidence_count": stmt.excluded.evidence_count,
                "shared_institution": stmt.excluded.shared_institution,
                "first_year": stmt.excluded.first_year,
                "last_year": stmt.excluded.last_year,
                "source_work_ids": stmt.excluded.source_work_ids,
            }
            await self.session.execute(
                stmt.on_conflict_do_update(
                    index_elements=["from_talent_id", "to_talent_id", "relationship_type"],
                    set_=update_dict,
                )
            )
        await self.session.flush()

    async def _prune_stale_edges(self, current_edges: list[dict[str, Any]]) -> None:
        """Remove edges that are no longer present or above min confidence.

        Uses a temp table + NOT EXISTS anti-join instead of a giant NOT IN
        clause. On 100k+ talents the old ``tuple_.in_(current_keys)`` approach
        generated a SQL string of tens of MB (hundreds of thousands of 3-tuples
        inlined into ``NOT IN (...)``), which crashed the PostgreSQL backend
        parser with a stack overflow.
        """
        if current_edges:
            # Keep set is batched into a temp table so the anti-join stays a
            # fixed-size SQL regardless of edge count. ON COMMIT DROP cleans up
            # automatically at the surrounding infer_all_genealogy() commit,
            # which runs after prune (same transaction).
            await self.session.execute(
                text(
                    "CREATE TEMP TABLE _genealogy_keep ("
                    " from_id INTEGER NOT NULL,"
                    " to_id INTEGER NOT NULL,"
                    " rel_type VARCHAR(20) NOT NULL"
                    ") ON COMMIT DROP"
                )
            )

            keep_keys = [
                (e["from_talent_id"], e["to_talent_id"], e["relationship_type"])
                for e in current_edges
            ]
            TEMP_BATCH = 5000
            for i in range(0, len(keep_keys), TEMP_BATCH):
                chunk = keep_keys[i : i + TEMP_BATCH]
                # Parameterized bulk insert: f/t/r prefixed per-row to keep
                # every value bound (no literal interpolation -> no injection).
                placeholders = ",".join(f"(:f{j},:t{j},:r{j})" for j in range(len(chunk)))
                params: dict[str, Any] = {}
                for j, (f_id, t_id, r_type) in enumerate(chunk):
                    params[f"f{j}"] = f_id
                    params[f"t{j}"] = t_id
                    params[f"r{j}"] = r_type
                await self.session.execute(
                    text(f"INSERT INTO _genealogy_keep VALUES {placeholders}"),
                    params,
                )

            # NOT EXISTS -> PostgreSQL picks a hash anti-join, no giant IN list.
            await self.session.execute(
                text(
                    "DELETE FROM genealogy_edge e "
                    "WHERE NOT EXISTS ("
                    " SELECT 1 FROM _genealogy_keep k "
                    " WHERE k.from_id = e.from_talent_id"
                    "   AND k.to_id = e.to_talent_id"
                    "   AND k.rel_type = e.relationship_type"
                    ")"
                )
            )

        # Belt and suspenders: also delete edges below min confidence
        await self.session.execute(
            GenealogyEdge.__table__.delete().where(GenealogyEdge.confidence_score < MIN_CONFIDENCE)
        )

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
        from app.domains.academic.models.genealogy import TalentInfluenceScore
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

    @staticmethod
    async def run_background_sync(
        progress_callback: Callable[..., Any] | None = None,
    ) -> dict[str, Any]:
        """Run the full genealogy background sync in a dedicated session.

        This factory-style entry point keeps AsyncSessionLocal out of the API
        layer and lets Service code own the background unit-of-work.

        Returns:
            dict with influence and genealogy result summaries.
        """
        from app.core.database import AsyncSessionLocal
        from app.domains.academic.services.influence_service import InfluenceService

        async with AsyncSessionLocal() as session:
            # Phase 1: Influence scores
            logger.info("[GenealogySync] Phase 1: Computing influence scores...")
            inf_service = InfluenceService(session)
            inf_result = await inf_service.compute_all_scores()
            await session.commit()
            logger.info(f"[GenealogySync] Influence scores computed: {inf_result}")

            # Phase 2: Genealogy inference
            logger.info("[GenealogySync] Phase 2: Inferring genealogy edges...")
            gen_service = GenealogyService(session)
            gen_result = await gen_service.infer_all_genealogy(progress_callback)
            await session.commit()
            logger.info(f"[GenealogySync] Genealogy inference completed: {gen_result}")

            return {"influence": inf_result, "genealogy": gen_result}
