"""
Collaboration service for extracting and managing co-author relationships.
"""
import asyncio
import httpx
from typing import List, Dict, Optional, Set, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.talent import Talent
from app.models.collaboration import Collaboration, WorkAuthor


class CollaborationService:
    """Service for managing collaboration data."""

    OPENALEX_WORKS_URL = "https://api.openalex.org/works"

    def __init__(self, session: AsyncSession):
        self.session = session
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def fetch_works_for_author(self, openalex_author_id: str, limit: int = 50) -> List[Dict]:
        """
        Fetch works from OpenAlex for a specific author.

        Args:
            openalex_author_id: OpenAlex author ID (e.g., "A123456789")
            limit: Maximum number of works to fetch

        Returns:
            List of work data from OpenAlex
        """
        try:
            # Construct author filter
            author_filter = f"author.id:{openalex_author_id}"

            params = {
                "filter": author_filter,
                "per_page": min(limit, 200),
                "sort": "cited_by_count:desc",
            }

            response = await self.client.get(self.OPENALEX_WORKS_URL, params=params)
            response.raise_for_status()

            data = response.json()
            return data.get("results", [])

        except Exception as e:
            print(f"Error fetching works for author {openalex_author_id}: {e}")
            return []

    def extract_authorships_from_work(self, work: Dict) -> List[Dict]:
        """
        Extract author information from a work.

        Returns list of author data with position and OpenAlex ID.
        """
        authorships = work.get("authorships", [])
        authors = []

        for authorship in authorships:
            author = authorship.get("author", {})
            author_id = author.get("id", "").split("/")[-1] if author.get("id") else None

            authors.append({
                "openalex_id": author_id,
                "name": author.get("display_name"),
                "position": authorship.get("author_position"),
                "is_corresponding": authorship.get("is_corresponding", False),
            })

        return authors

    async def sync_collaborations_for_talent(
        self,
        talent: Talent,
        limit: int = 50
    ) -> int:
        """
        Sync collaboration data for a single talent.

        Returns number of collaborations created/updated.
        """
        if not talent.source_record_id:
            return 0

        # Extract OpenAlex author ID from source_record_id
        openalex_id = talent.source_record_id.split("/")[-1] if "/" in talent.source_record_id else talent.source_record_id

        # Fetch works
        works = await self.fetch_works_for_author(openalex_id, limit)
        if not works:
            return 0

        collaboration_count = 0
        openalex_to_talent = {}  # Cache for OpenAlex ID -> talent_id mapping

        for work in works:
            work_id = work.get("id", "").split("/")[-1]
            publication_year = work.get("publication_year")
            authors = self.extract_authorships_from_work(work)

            # Find talent IDs for authors
            talent_ids = []
            for author in authors:
                if author["openalex_id"]:
                    if author["openalex_id"] in openalex_to_talent:
                        talent_ids.append(openalex_to_talent[author["openalex_id"]])
                    else:
                        # Look up talent by OpenAlex ID
                        stmt = select(Talent).where(
                            Talent.source_record_id.like(f"%{author['openalex_id']}")
                        )
                        result = await self.session.execute(stmt)
                        author_talent = result.scalar_one_or_none()

                        if author_talent:
                            openalex_to_talent[author["openalex_id"]] = author_talent.talent_id
                            talent_ids.append(author_talent.talent_id)

            # Create collaborations between all pairs of talents in this work
            for i in range(len(talent_ids)):
                for j in range(i + 1, len(talent_ids)):
                    t1, t2 = min(talent_ids[i], talent_ids[j]), max(talent_ids[i], talent_ids[j])

                    if t1 == t2:
                        continue

                    # Check if collaboration exists
                    stmt = select(Collaboration).where(
                        and_(
                            Collaboration.talent_id_1 == t1,
                            Collaboration.talent_id_2 == t2
                        )
                    )
                    result = await self.session.execute(stmt)
                    collab = result.scalar_one_or_none()

                    if collab:
                        # Update existing collaboration
                        collab.collaboration_count += 1
                        if publication_year:
                            if collab.first_collaboration_year:
                                collab.first_collaboration_year = min(collab.first_collaboration_year, publication_year)
                                collab.last_collaboration_year = max(collab.last_collaboration_year, publication_year)
                            else:
                                collab.first_collaboration_year = publication_year
                                collab.last_collaboration_year = publication_year
                    else:
                        # Create new collaboration
                        collab = Collaboration(
                            talent_id_1=t1,
                            talent_id_2=t2,
                            collaboration_count=1,
                            first_collaboration_year=publication_year,
                            last_collaboration_year=publication_year,
                        )
                        self.session.add(collab)
                        collaboration_count += 1

        await self.session.commit()
        return collaboration_count

    async def get_collaboration_network(
        self,
        talent_id: int,
        limit: int = 20
    ) -> Dict:
        """
        Get collaboration network for a talent.

        Returns nodes and links for visualization.
        """
        # Get all collaborations for this talent
        stmt = select(Collaboration).where(
            or_(
                Collaboration.talent_id_1 == talent_id,
                Collaboration.talent_id_2 == talent_id
            )
        ).order_by(Collaboration.collaboration_count.desc()).limit(limit)

        result = await self.session.execute(stmt)
        collaborations = result.scalars().all()

        if not collaborations:
            return {"nodes": [], "links": [], "message": "暂无合作网络数据"}

        # Get the main talent
        main_talent_stmt = select(Talent).where(Talent.talent_id == talent_id)
        main_talent_result = await self.session.execute(main_talent_stmt)
        main_talent = main_talent_result.scalar_one_or_none()

        if not main_talent:
            return {"nodes": [], "links": [], "message": "人才不存在"}

        # Collect all collaborator IDs
        collaborator_ids = set()
        for collab in collaborations:
            if collab.talent_id_1 == talent_id:
                collaborator_ids.add(collab.talent_id_2)
            else:
                collaborator_ids.add(collab.talent_id_1)

        # Fetch all collaborators
        stmt = select(Talent).where(Talent.talent_id.in_(collaborator_ids))
        result = await self.session.execute(stmt)
        collaborators = {t.talent_id: t for t in result.scalars().all()}

        # Build nodes
        nodes = [
            {
                "id": str(talent_id),
                "name": main_talent.name,
                "affiliation": main_talent.school.school_name if main_talent.school else None,
                "isMain": True,
                "collaborationCount": sum(c.collaboration_count for c in collaborations),
            }
        ]

        for collab_id in collaborator_ids:
            collab_talent = collaborators.get(collab_id)
            if collab_talent:
                # Find collaboration count
                collab_count = 0
                for c in collaborations:
                    if (c.talent_id_1 == talent_id and c.talent_id_2 == collab_id) or \
                       (c.talent_id_2 == talent_id and c.talent_id_1 == collab_id):
                        collab_count = c.collaboration_count
                        break

                nodes.append({
                    "id": str(collab_id),
                    "name": collab_talent.name,
                    "affiliation": collab_talent.school.school_name if collab_talent.school else None,
                    "isMain": False,
                    "collaborationCount": collab_count,
                })

        # Build links
        links = []
        for collab in collaborations:
            other_id = collab.talent_id_2 if collab.talent_id_1 == talent_id else collab.talent_id_1
            links.append({
                "source": str(talent_id),
                "target": str(other_id),
                "value": collab.collaboration_count,
            })

        return {
            "nodes": nodes,
            "links": links,
            "total": len(nodes) - 1,
        }

    async def generate_sample_collaborations(self, num_samples: int = 100) -> int:
        """
        Generate sample collaboration data for testing.

        This creates random collaborations between talents in the database.
        """
        import random

        # Get all talents
        stmt = select(Talent.talent_id)
        result = await self.session.execute(stmt)
        talent_ids = [row[0] for row in result.fetchall()]

        if len(talent_ids) < 2:
            return 0

        collaborations_created = 0

        for _ in range(num_samples):
            # Pick two random talents
            t1, t2 = random.sample(talent_ids, 2)
            t1, t2 = min(t1, t2), max(t1, t2)  # Ensure consistent ordering

            # Check if collaboration already exists
            stmt = select(Collaboration).where(
                and_(
                    Collaboration.talent_id_1 == t1,
                    Collaboration.talent_id_2 == t2
                )
            )
            result = await self.session.execute(stmt)
            if result.scalar_one_or_none():
                continue

            # Create collaboration
            collab = Collaboration(
                talent_id_1=t1,
                talent_id_2=t2,
                collaboration_count=random.randint(1, 10),
                first_collaboration_year=random.randint(2018, 2024),
                last_collaboration_year=random.randint(2022, 2025),
            )
            self.session.add(collab)
            collaborations_created += 1

        await self.session.commit()
        return collaborations_created
