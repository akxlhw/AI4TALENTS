"""Tests for repo collected-data purge (预览/硬删除 + 归属判定 + 保护名单 + 权限)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, hash_password
from app.core.exceptions import NotFoundError
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
    OSTalentPool,
)
from app.domains.open_source.repositories.open_source import OpenSourceRepository
from app.domains.open_source.services.os_collection_service import OSCollectionService
from app.domains.shared.models.enums import UserRoleType
from app.domains.shared.models.iam import UserAccount


def _make_developer(github_login: str, github_id: int) -> OSDeveloper:
    return OSDeveloper(
        github_login=github_login,
        github_id=github_id,
        name=github_login,
        primary_languages=["Python"],
        tech_tags=["ai"],
        is_visible=True,
    )


def _make_repo(owner: OSDeveloper, full_name: str, github_repo_id: int) -> OSRepository:
    return OSRepository(
        developer_id=owner.developer_id,
        github_repo_id=github_repo_id,
        full_name=full_name,
        name=full_name.split("/")[-1],
        language="Python",
        stars_count=100,
        forks_count=10,
        topics=[],
        is_fork=False,
    )


async def _make_user(test_session: AsyncSession, username: str) -> UserAccount:
    user = UserAccount(
        username=username,
        email=f"{username}@example.com",
        password_hash=hash_password("testpassword123"),
        role_type=UserRoleType.USER.value,
        is_active=True,
        display_name=username,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


async def _seed_shared_scenario(test_session: AsyncSession) -> dict:
    """Seed repo R (org/r1, owner devA) with contributors devA/devB; devB also contributes to R2.

    devA is exclusive to R; devB is shared with the *configured* repo R2.
    """
    config = OSRepoConfig(
        repo_full_name="org/r1",
        display_name="R1",
        tech_element=["models"],
        is_active=True,
        collect_enabled=True,
    )
    config_r2 = OSRepoConfig(
        repo_full_name="org/r2",
        display_name="R2",
        tech_element=["models"],
        is_active=True,
        collect_enabled=True,
    )
    dev_a = _make_developer("dev-exclusive", 9001)
    dev_b = _make_developer("dev-shared", 9002)
    test_session.add_all([config, config_r2, dev_a, dev_b])
    await test_session.commit()

    r1 = _make_repo(dev_a, "org/r1", 9101)
    r2 = _make_repo(dev_b, "org/r2", 9102)
    test_session.add_all([r1, r2])
    await test_session.commit()

    test_session.add_all(
        [
            OSContribution(developer_id=dev_a.developer_id, repo_id=r1.repo_id, commits_count=10),
            OSContribution(developer_id=dev_b.developer_id, repo_id=r1.repo_id, commits_count=5),
            OSContribution(developer_id=dev_b.developer_id, repo_id=r2.repo_id, commits_count=3),
        ]
    )
    await test_session.commit()
    return {"config": config, "dev_a": dev_a, "dev_b": dev_b, "r1": r1, "r2": r2}


async def _add_cascades(test_session: AsyncSession, dev: OSDeveloper) -> None:
    """Add language skill / embedding / raw data for a developer."""
    test_session.add_all(
        [
            OSLanguageSkill(developer_id=dev.developer_id, language="Python"),
            OSEmbedding(developer_id=dev.developer_id, embedding="0.1,0.2,0.3"),
            OSRawDeveloper(github_login=dev.github_login, raw_data={"login": dev.github_login}),
        ]
    )
    await test_session.commit()


async def _count(test_session: AsyncSession, model, *conditions) -> int:
    stmt = select(func.count()).select_from(model)
    if conditions:
        stmt = stmt.where(*conditions)
    return await test_session.scalar(stmt) or 0


class TestRepoPurgeRepository:
    @pytest.mark.asyncio
    async def test_purge_deletes_exclusive_and_keeps_shared(self, test_session: AsyncSession):
        data = await _seed_shared_scenario(test_session)
        dev_a, dev_b = data["dev_a"], data["dev_b"]
        await _add_cascades(test_session, dev_a)
        await _add_cascades(test_session, dev_b)

        repo = OpenSourceRepository(test_session)
        result = await repo.purge_repo_data("org/r1")

        assert result["repo_found"] is True
        assert result["contributions"] == 2
        assert result["developers_total"] == 2
        assert result["developers_exclusive"] == 1
        assert result["developers_protected"] == 0
        assert result["developers_shared"] == 1
        assert result["skills"] == 1
        assert result["embeddings"] == 1
        assert result["raw"] == 1

        # 独占人才及其级联数据已删除
        assert (
            await _count(test_session, OSDeveloper, OSDeveloper.developer_id == dev_a.developer_id)
            == 0
        )
        assert (
            await _count(
                test_session, OSLanguageSkill, OSLanguageSkill.developer_id == dev_a.developer_id
            )
            == 0
        )
        assert (
            await _count(test_session, OSEmbedding, OSEmbedding.developer_id == dev_a.developer_id)
            == 0
        )
        assert (
            await _count(
                test_session, OSRawDeveloper, OSRawDeveloper.github_login == "dev-exclusive"
            )
            == 0
        )

        # 共享人才及其级联数据保留
        assert (
            await _count(test_session, OSDeveloper, OSDeveloper.developer_id == dev_b.developer_id)
            == 1
        )
        assert (
            await _count(
                test_session, OSLanguageSkill, OSLanguageSkill.developer_id == dev_b.developer_id
            )
            == 1
        )
        assert (
            await _count(test_session, OSRawDeveloper, OSRawDeveloper.github_login == "dev-shared")
            == 1
        )

        # R 的贡献与仓库行已删除；R2 不受影响
        assert (
            await _count(test_session, OSContribution, OSContribution.repo_id == data["r1"].repo_id)
            == 0
        )
        assert await _count(test_session, OSRepository, OSRepository.full_name == "org/r1") == 0
        assert (
            await _count(test_session, OSContribution, OSContribution.repo_id == data["r2"].repo_id)
            == 1
        )
        assert await _count(test_session, OSRepository, OSRepository.full_name == "org/r2") == 1

    @pytest.mark.asyncio
    async def test_preview_does_not_delete(self, test_session: AsyncSession):
        data = await _seed_shared_scenario(test_session)
        await _add_cascades(test_session, data["dev_a"])

        repo = OpenSourceRepository(test_session)
        preview = await repo.get_repo_purge_preview("org/r1")

        assert preview["repo_found"] is True
        assert preview["contributions"] == 2
        assert preview["developers_total"] == 2
        assert preview["developers_exclusive"] == 1
        assert preview["developers_shared"] == 1
        assert preview["skills"] == 1
        assert preview["embeddings"] == 1
        assert preview["raw"] == 1

        # dry_run 不落任何删除
        assert await _count(test_session, OSDeveloper) == 2
        assert await _count(test_session, OSContribution) == 3
        assert await _count(test_session, OSRepository) == 2

    @pytest.mark.asyncio
    async def test_purge_protects_favourited_developer(self, test_session: AsyncSession):
        data = await _seed_shared_scenario(test_session)
        dev_a = data["dev_a"]
        await _add_cascades(test_session, dev_a)
        user = await _make_user(test_session, "purge_fav_user")
        test_session.add(
            OSFavourite(user_id=user.user_id, developer_id=dev_a.developer_id, is_active=True)
        )
        await test_session.commit()

        repo = OpenSourceRepository(test_session)
        result = await repo.purge_repo_data("org/r1")

        assert result["developers_exclusive"] == 0
        assert result["developers_protected"] == 1
        assert result["skills"] == 0
        # 被收藏人才及其级联数据保留，但贡献记录仍删除
        assert (
            await _count(test_session, OSDeveloper, OSDeveloper.developer_id == dev_a.developer_id)
            == 1
        )
        assert (
            await _count(
                test_session, OSLanguageSkill, OSLanguageSkill.developer_id == dev_a.developer_id
            )
            == 1
        )
        assert (
            await _count(
                test_session, OSRawDeveloper, OSRawDeveloper.github_login == "dev-exclusive"
            )
            == 1
        )
        assert (
            await _count(test_session, OSContribution, OSContribution.repo_id == data["r1"].repo_id)
            == 0
        )
        assert await _count(test_session, OSRepository, OSRepository.full_name == "org/r1") == 0

    @pytest.mark.asyncio
    async def test_purge_protects_pool_member(self, test_session: AsyncSession):
        data = await _seed_shared_scenario(test_session)
        dev_a = data["dev_a"]
        user = await _make_user(test_session, "purge_pool_user")
        pool = OSTalentPool(
            owner_user_id=user.user_id,
            pool_name="Purge Pool",
            pool_status="active",
        )
        test_session.add(pool)
        await test_session.commit()
        test_session.add(OSPoolMember(pool_id=pool.pool_id, developer_id=dev_a.developer_id))
        await test_session.commit()

        repo = OpenSourceRepository(test_session)
        result = await repo.purge_repo_data("org/r1")

        assert result["developers_exclusive"] == 0
        assert result["developers_protected"] == 1
        assert (
            await _count(test_session, OSDeveloper, OSDeveloper.developer_id == dev_a.developer_id)
            == 1
        )

    @pytest.mark.asyncio
    async def test_purge_repo_not_collected(self, test_session: AsyncSession):
        """配置存在但未采集过（无 os_repository 行）时返回 repo_found=False。"""
        config = OSRepoConfig(
            repo_full_name="org/never-collected",
            display_name="NC",
            tech_element=["models"],
            is_active=True,
            collect_enabled=True,
        )
        test_session.add(config)
        await test_session.commit()

        repo = OpenSourceRepository(test_session)
        preview = await repo.get_repo_purge_preview("org/never-collected")
        assert preview["repo_found"] is False
        assert preview["contributions"] == 0
        assert preview["developers_total"] == 0

        result = await repo.purge_repo_data("org/never-collected")
        assert result["repo_found"] is False
        assert result["developers_exclusive"] == 0

    @pytest.mark.asyncio
    async def test_purge_unconfigured_references_count_as_exclusive(
        self, test_session: AsyncSession
    ):
        """只拥有未配置个人仓库 / 只对未配置仓库有贡献的人才判独占，连同其未配置仓库一并删除。"""
        config = OSRepoConfig(
            repo_full_name="org/r1",
            display_name="R1",
            tech_element=["models"],
            is_active=True,
            collect_enabled=True,
        )
        dev_c = _make_developer("dev-personal-repo", 9003)
        dev_d = _make_developer("dev-unconfigured-contrib", 9004)
        test_session.add_all([config, dev_c, dev_d])
        await test_session.commit()

        r1 = _make_repo(dev_c, "org/r1", 9103)
        personal = _make_repo(dev_c, "devc/personal-repo", 9104)
        other = _make_repo(dev_d, "other/unconfigured", 9105)
        test_session.add_all([r1, personal, other])
        await test_session.commit()

        test_session.add_all(
            [
                OSContribution(
                    developer_id=dev_c.developer_id, repo_id=r1.repo_id, commits_count=8
                ),
                OSContribution(
                    developer_id=dev_d.developer_id, repo_id=r1.repo_id, commits_count=4
                ),
                OSContribution(
                    developer_id=dev_d.developer_id, repo_id=other.repo_id, commits_count=2
                ),
            ]
        )
        await test_session.commit()

        repo = OpenSourceRepository(test_session)
        preview = await repo.get_repo_purge_preview("org/r1")
        assert preview["developers_total"] == 2
        assert preview["developers_exclusive"] == 2
        assert preview["developers_shared"] == 0
        # R1 的 2 条贡献 + dev_d 对未配置仓库的 1 条贡献
        assert preview["contributions"] == 3

        result = await repo.purge_repo_data("org/r1")
        assert result["developers_exclusive"] == 2
        assert result["developers_shared"] == 0
        assert result["contributions"] == 3

        # 两名独占人才已删除
        assert (
            await _count(test_session, OSDeveloper, OSDeveloper.developer_id == dev_c.developer_id)
            == 0
        )
        assert (
            await _count(test_session, OSDeveloper, OSDeveloper.developer_id == dev_d.developer_id)
            == 0
        )
        # 其拥有的未配置仓库与相关贡献也已级联删除
        assert (
            await _count(test_session, OSRepository, OSRepository.full_name == "devc/personal-repo")
            == 0
        )
        assert (
            await _count(test_session, OSRepository, OSRepository.full_name == "other/unconfigured")
            == 0
        )
        assert await _count(test_session, OSContribution) == 0
        assert await _count(test_session, OSRepository) == 0


class TestRepoPurgeService:
    @pytest.mark.asyncio
    async def test_preview_raises_not_found_for_missing_config(self, test_session: AsyncSession):
        service = OSCollectionService(test_session)
        with pytest.raises(NotFoundError):
            await service.preview_repo_purge(999999)

    @pytest.mark.asyncio
    async def test_purge_delete_config_removes_config_row(self, test_session: AsyncSession):
        data = await _seed_shared_scenario(test_session)
        config = data["config"]

        service = OSCollectionService(test_session)
        result = await service.purge_repo(config.repo_config_id, delete_config=True)

        assert result.config_deleted is True
        assert result.developers_exclusive == 1
        assert (
            await _count(
                test_session, OSRepoConfig, OSRepoConfig.repo_config_id == config.repo_config_id
            )
            == 0
        )

    @pytest.mark.asyncio
    async def test_purge_keeps_config_by_default(self, test_session: AsyncSession):
        data = await _seed_shared_scenario(test_session)
        config = data["config"]

        service = OSCollectionService(test_session)
        result = await service.purge_repo(config.repo_config_id, delete_config=False)

        assert result.config_deleted is False
        assert (
            await _count(
                test_session, OSRepoConfig, OSRepoConfig.repo_config_id == config.repo_config_id
            )
            == 1
        )


class TestRepoPurgeApi:
    @pytest.mark.asyncio
    async def test_purge_forbidden_for_normal_admin(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        data = await _seed_shared_scenario(test_session)
        admin = UserAccount(
            username="purge_admin",
            email="purge_admin@example.com",
            password_hash=hash_password("adminpassword123"),
            role_type=UserRoleType.ADMIN.value,
            is_active=True,
            display_name="Purge Admin",
        )
        test_session.add(admin)
        await test_session.commit()
        token = create_access_token(
            user_id=admin.user_id, username=admin.username, role=admin.role_type
        )

        response = await client.post(
            f"/api/v1/open-source/repo-configs/{data['config'].repo_config_id}/purge",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_purge_as_super_admin_dry_run_default(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        data = await _seed_shared_scenario(test_session)
        super_admin = UserAccount(
            username="purge_super_admin",
            email="purge_super_admin@example.com",
            password_hash=hash_password("superadminpassword123"),
            role_type=UserRoleType.SUPER_ADMIN.value,
            is_active=True,
            display_name="Purge Super Admin",
        )
        test_session.add(super_admin)
        await test_session.commit()
        token = create_access_token(
            user_id=super_admin.user_id,
            username=super_admin.username,
            role=super_admin.role_type,
        )
        headers = {"Authorization": f"Bearer {token}"}
        url = f"/api/v1/open-source/repo-configs/{data['config'].repo_config_id}/purge"

        # 默认 dry_run=true，只预览不删除
        response = await client.post(url, headers=headers)
        assert response.status_code == 200
        preview = response.json()
        assert preview["repo_full_name"] == "org/r1"
        assert preview["repo_found"] is True
        assert preview["developers_exclusive"] == 1
        assert preview["developers_shared"] == 1
        assert await _count(test_session, OSDeveloper) == 2

        # 实删
        response = await client.post(url, params={"dry_run": False}, headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert result["developers_exclusive"] == 1
        assert result["config_deleted"] is False
        assert await _count(test_session, OSDeveloper) == 1
        assert await _count(test_session, OSRepository, OSRepository.full_name == "org/r1") == 0

    @pytest.mark.asyncio
    async def test_purge_missing_config_returns_404(
        self, client: AsyncClient, test_session: AsyncSession
    ):
        super_admin = UserAccount(
            username="purge_super_admin_404",
            email="purge_super_admin_404@example.com",
            password_hash=hash_password("superadminpassword123"),
            role_type=UserRoleType.SUPER_ADMIN.value,
            is_active=True,
            display_name="Purge Super Admin 404",
        )
        test_session.add(super_admin)
        await test_session.commit()
        token = create_access_token(
            user_id=super_admin.user_id,
            username=super_admin.username,
            role=super_admin.role_type,
        )

        response = await client.post(
            "/api/v1/open-source/repo-configs/999999/purge",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
