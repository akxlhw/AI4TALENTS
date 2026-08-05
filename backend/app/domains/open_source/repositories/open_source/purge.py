"""
Open Source Repository - purge queries.

Split from core.py; methods are mixed into OpenSourceCoreRepository.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from typing import cast as tcast

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSContribution,
    OSDeveloper,
    OSEmbedding,
    OSFavourite,
    OSLanguageSkill,
    OSPoolMember,
    OSRawDeveloper,
    OSRepoConfig,
    OSRepository,
)


class PurgeMixin:
    """Repo purge, embedding gap and misc query operations."""

    session: AsyncSession

    if TYPE_CHECKING:
        # Provided by DevelopersMixin on the composed OpenSourceCoreRepository
        async def get_repository_by_full_name(self, full_name: str) -> OSRepository | None: ...

    async def get_missing_developer_ids(
        self,
        developer_ids: list[int],
        model_name: str | None = None,
        vector_type: str | None = None,
    ) -> list[int]:
        """Get developer IDs that do not have embeddings."""
        if not developer_ids:
            return []

        BATCH_SIZE = 5000
        existing_ids: set[int] = set()

        for i in range(0, len(developer_ids), BATCH_SIZE):
            batch_ids = developer_ids[i : i + BATCH_SIZE]
            query = select(OSEmbedding.developer_id).where(OSEmbedding.developer_id.in_(batch_ids))
            if model_name:
                query = query.where(OSEmbedding.model_name == model_name)
            if vector_type:
                query = query.where(OSEmbedding.vector_type == vector_type)
            result = await self.session.execute(query)
            for row in result.fetchall():
                existing_ids.add(row[0])

        return [did for did in developer_ids if did not in existing_ids]

    async def get_visible_developer_ids(self) -> list[int]:
        """Get all visible developer IDs."""
        result = await self.session.execute(
            select(OSDeveloper.developer_id)
            .where(OSDeveloper.is_visible.is_(True))
            .order_by(OSDeveloper.developer_id)
        )
        return [row[0] for row in result.fetchall()]

    async def get_repositories_for_developers(
        self,
        developer_ids: list[int],
    ) -> dict[int, list[OSRepository]]:
        """Batch get repositories for multiple developers, ordered by stars desc."""
        if not developer_ids:
            return {}
        result = await self.session.execute(
            select(OSRepository)
            .where(OSRepository.developer_id.in_(developer_ids))
            .order_by(OSRepository.developer_id, OSRepository.stars_count.desc())
        )
        mapping: dict[int, list[OSRepository]] = {}
        for repo in result.scalars().all():
            dev_id = tcast(int, repo.developer_id)
            if dev_id not in mapping:
                mapping[dev_id] = []
            mapping[dev_id].append(repo)
        return mapping

    async def get_raw_developers_by_logins(
        self,
        github_logins: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Batch get raw developer data by GitHub logins."""
        if not github_logins:
            return {}
        result = await self.session.execute(
            select(OSRawDeveloper).where(OSRawDeveloper.github_login.in_(github_logins))
        )
        mapping: dict[str, dict[str, Any]] = {}
        for raw in result.scalars().all():
            login = tcast(str, raw.github_login)
            mapping[login] = tcast("dict[str, Any] | None", raw.raw_data) or {}
        return mapping

    # ========== Repo Data Purge ==========

    @staticmethod
    def _empty_purge_counts() -> dict[str, Any]:
        """Zeroed purge counts used when the repo has no collected data."""
        return {
            "repo_found": False,
            "contributions": 0,
            "developers_total": 0,
            "developers_exclusive": 0,
            "developers_protected": 0,
            "developers_shared": 0,
            "skills": 0,
            "embeddings": 0,
            "raw": 0,
        }

    async def _classify_repo_developers(
        self,
        repo: OSRepository,
    ) -> dict[str, set[int]]:
        """Classify developers involved with a repo for purge.

        Involved developers = contributors of this repo + repo owner.
        Returns disjoint sets of developer IDs:
        - exclusive: not referenced by any other *configured* repo (i.e. a repo whose
          full_name exists in os_repo_config); will be deleted
        - protected: exclusive to this repo but kept due to active favourite or pool membership
        - shared: still referenced by other configured repos (contribution or ownership); kept

        References to unconfigured repos (e.g. personal repos fetched alongside
        contributor profiles) do not count as shared.
        """
        repo_id = tcast(int, repo.repo_id)
        owner_id = tcast(int, repo.developer_id)

        contributor_rows = await self.session.execute(
            select(OSContribution.developer_id).where(OSContribution.repo_id == repo_id)
        )
        involved_ids: set[int] = {tcast(int, row[0]) for row in contributor_rows.all()}
        involved_ids.add(owner_id)

        if not involved_ids:
            return {"exclusive": set(), "protected": set(), "shared": set()}

        configured_names = select(OSRepoConfig.repo_full_name)
        other_contrib_rows = await self.session.execute(
            select(OSContribution.developer_id)
            .join(OSRepository, OSContribution.repo_id == OSRepository.repo_id)
            .where(
                OSContribution.developer_id.in_(involved_ids),
                OSContribution.repo_id != repo_id,
                OSRepository.full_name.in_(configured_names),
            )
            .distinct()
        )
        other_owner_rows = await self.session.execute(
            select(OSRepository.developer_id)
            .where(
                OSRepository.developer_id.in_(involved_ids),
                OSRepository.repo_id != repo_id,
                OSRepository.full_name.in_(configured_names),
            )
            .distinct()
        )
        shared_ids = {tcast(int, row[0]) for row in other_contrib_rows.all()}
        shared_ids.update(tcast(int, row[0]) for row in other_owner_rows.all())

        candidate_ids = involved_ids - shared_ids
        protected_ids: set[int] = set()
        if candidate_ids:
            favourite_rows = await self.session.execute(
                select(OSFavourite.developer_id)
                .where(
                    OSFavourite.developer_id.in_(candidate_ids),
                    OSFavourite.is_active.is_(True),
                )
                .distinct()
            )
            protected_ids.update(tcast(int, row[0]) for row in favourite_rows.all())
            pool_rows = await self.session.execute(
                select(OSPoolMember.developer_id)
                .where(OSPoolMember.developer_id.in_(candidate_ids))
                .distinct()
            )
            protected_ids.update(tcast(int, row[0]) for row in pool_rows.all())

        return {
            "exclusive": candidate_ids - protected_ids,
            "protected": protected_ids,
            "shared": shared_ids,
        }

    async def _count_exclusive_cascades(self, exclusive_ids: set[int]) -> dict[str, int]:
        """Count language skills / embeddings / raw data belonging to exclusive developers."""
        counts = {"skills": 0, "embeddings": 0, "raw": 0}
        if not exclusive_ids:
            return counts

        counts["skills"] = (
            await self.session.scalar(
                select(func.count())
                .select_from(OSLanguageSkill)
                .where(OSLanguageSkill.developer_id.in_(exclusive_ids))
            )
            or 0
        )
        counts["embeddings"] = (
            await self.session.scalar(
                select(func.count())
                .select_from(OSEmbedding)
                .where(OSEmbedding.developer_id.in_(exclusive_ids))
            )
            or 0
        )
        login_rows = await self.session.execute(
            select(OSDeveloper.github_login).where(OSDeveloper.developer_id.in_(exclusive_ids))
        )
        logins = [tcast(str, row[0]) for row in login_rows.all()]
        if logins:
            counts["raw"] = (
                await self.session.scalar(
                    select(func.count())
                    .select_from(OSRawDeveloper)
                    .where(OSRawDeveloper.github_login.in_(logins))
                )
                or 0
            )
        return counts

    async def _exclusive_owned_repo_ids(self, exclusive_ids: set[int]) -> set[int]:
        """Repo IDs owned by exclusive developers.

        Under the configured-repo sharing rule an exclusive developer may still own
        unconfigured repos (e.g. personal repos); those rows reference
        os_developer via FK and must be cascade-deleted together with the developer.
        """
        if not exclusive_ids:
            return set()
        rows = await self.session.execute(
            select(OSRepository.repo_id).where(OSRepository.developer_id.in_(exclusive_ids))
        )
        return {tcast(int, row[0]) for row in rows.all()}

    def _purge_contribution_conditions(
        self,
        repo_id: int,
        exclusive_ids: set[int],
        owned_repo_ids: set[int],
    ) -> list[Any]:
        """Conditions matching every contribution row a purge will delete:
        this repo's contributions + contributions to repos owned by exclusive
        developers + exclusive developers' own contributions to any other repo."""
        conditions: list[Any] = [OSContribution.repo_id == repo_id]
        if owned_repo_ids:
            conditions.append(OSContribution.repo_id.in_(owned_repo_ids))
        if exclusive_ids:
            conditions.append(OSContribution.developer_id.in_(exclusive_ids))
        return conditions

    async def get_repo_purge_preview(self, repo_full_name: str) -> dict[str, Any]:
        """Compute purge impact counts for a repo's collected data (no deletion)."""
        repo = await self.get_repository_by_full_name(repo_full_name)
        if repo is None:
            return self._empty_purge_counts()

        classification = await self._classify_repo_developers(repo)
        exclusive_ids = classification["exclusive"]
        owned_repo_ids = await self._exclusive_owned_repo_ids(exclusive_ids)
        contributions = (
            await self.session.scalar(
                select(func.count())
                .select_from(OSContribution)
                .where(
                    or_(
                        *self._purge_contribution_conditions(
                            tcast(int, repo.repo_id), exclusive_ids, owned_repo_ids
                        )
                    )
                )
            )
            or 0
        )
        cascades = await self._count_exclusive_cascades(exclusive_ids)

        return {
            "repo_found": True,
            "contributions": contributions,
            "developers_total": sum(len(ids) for ids in classification.values()),
            "developers_exclusive": len(exclusive_ids),
            "developers_protected": len(classification["protected"]),
            "developers_shared": len(classification["shared"]),
            **cascades,
        }

    async def purge_repo_data(self, repo_full_name: str) -> dict[str, Any]:
        """Hard-delete collected data for a repo.

        Deletion order: all affected contributions (this repo's + repos owned by
        exclusive developers + exclusive developers' other contributions) -> repo
        row (exclusive developers may own this repo) -> other repos owned by
        exclusive developers -> exclusive developers' language skills / embeddings /
        raw data -> exclusive developers.
        Shared and protected developers are kept; collect task history is preserved.
        """
        repo = await self.get_repository_by_full_name(repo_full_name)
        if repo is None:
            return self._empty_purge_counts()

        repo_id = tcast(int, repo.repo_id)
        classification = await self._classify_repo_developers(repo)
        exclusive_ids = classification["exclusive"]
        owned_repo_ids = await self._exclusive_owned_repo_ids(exclusive_ids)

        contrib_result = await self.session.execute(
            delete(OSContribution).where(
                or_(*self._purge_contribution_conditions(repo_id, exclusive_ids, owned_repo_ids))
            )
        )
        contributions = contrib_result.rowcount or 0

        # 先删仓库行 R：独占人才可能就是 R 的属主，os_repository.developer_id 有外键约束
        await self.session.delete(repo)
        await self.session.flush()

        # 级联删除独占人才拥有的其他仓库（未配置的个人仓库等，同样有外键约束）
        other_owned_ids = owned_repo_ids - {repo_id}
        if other_owned_ids:
            await self.session.execute(
                delete(OSRepository).where(OSRepository.repo_id.in_(other_owned_ids))
            )

        skills = embeddings = raw = 0
        if exclusive_ids:
            skills = (
                await self.session.execute(
                    delete(OSLanguageSkill).where(OSLanguageSkill.developer_id.in_(exclusive_ids))
                )
            ).rowcount or 0
            embeddings = (
                await self.session.execute(
                    delete(OSEmbedding).where(OSEmbedding.developer_id.in_(exclusive_ids))
                )
            ).rowcount or 0
            login_rows = await self.session.execute(
                select(OSDeveloper.github_login).where(OSDeveloper.developer_id.in_(exclusive_ids))
            )
            logins = [tcast(str, row[0]) for row in login_rows.all()]
            if logins:
                raw = (
                    await self.session.execute(
                        delete(OSRawDeveloper).where(OSRawDeveloper.github_login.in_(logins))
                    )
                ).rowcount or 0
            await self.session.execute(
                delete(OSDeveloper).where(OSDeveloper.developer_id.in_(exclusive_ids))
            )

        await self.session.commit()

        return {
            "repo_found": True,
            "contributions": contributions,
            "developers_total": sum(len(ids) for ids in classification.values()),
            "developers_exclusive": len(exclusive_ids),
            "developers_protected": len(classification["protected"]),
            "developers_shared": len(classification["shared"]),
            "skills": skills,
            "embeddings": embeddings,
            "raw": raw,
        }

    async def get_collected_repos_for_developers(
        self,
        developer_ids: list[int],
    ) -> dict[int, list[str]]:
        """Get collected repo full_names that the developers have contributed to.
        Only includes repos configured in OSRepoConfig (system-collected sources),
        excluding personal repos that were fetched alongside contributor profiles.
        """
        if not developer_ids:
            return {}
        result = await self.session.execute(
            select(OSContribution.developer_id, OSRepository.full_name)
            .join(OSRepository, OSContribution.repo_id == OSRepository.repo_id)
            .join(OSRepoConfig, OSRepository.full_name == OSRepoConfig.repo_full_name)
            .where(
                OSContribution.developer_id.in_(developer_ids),
                OSRepoConfig.is_active.is_(True),
            )
            .distinct()
            .order_by(OSContribution.developer_id, OSRepository.full_name)
        )
        mapping: dict[int, list[str]] = {}
        for dev_id, full_name in result.all():
            if dev_id not in mapping:
                mapping[dev_id] = []
            mapping[dev_id].append(full_name)
        return mapping
