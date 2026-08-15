"""Tests for candidate score editing and single-link removal.

Covers two admin operations on the position-talent link:
- PATCH /industry/talents/{id}/positions/{pid} with score fields
- DELETE /industry/talents/{id}/positions/{pid} (remove from one position)
"""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.industry.models.industry import (
    IndustryPosition,
    IndustryPositionTalent,
    IndustryTalent,
)
from app.domains.industry.services.industry_import_service import IndustryImportService
from app.domains.shared.api.auth import get_current_user
from app.main import app


def _jsonl(*records: dict) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in records)


@pytest.fixture
async def admin_client(client: AsyncClient, test_session: AsyncSession) -> AsyncClient:
    """super_admin client backed by a real user row."""
    from app.domains.shared.models.iam import UserAccount

    user = UserAccount(
        username="score_admin",
        email="score_admin@example.com",
        password_hash="x",
        role_type="super_admin",
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": user.user_id,
        "username": "score_admin",
        "role": "super_admin",
    }
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def user_client(client: AsyncClient) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 1,
        "username": "normal_user",
        "role": "user",
    }
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def _seed_candidates(
    test_session: AsyncSession,
) -> tuple[IndustryPosition, IndustryPosition, int, int]:
    """Create two positions with shared candidates. Returns (p1, p2, zhangsan_id, lisi_id)."""
    p1 = IndustryPosition(title="岗位A", status="open")
    p2 = IndustryPosition(title="岗位B", status="open")
    test_session.add_all([p1, p2])
    await test_session.commit()

    service = IndustryImportService(test_session)
    # 张三 matches both positions; 李四 matches only p1
    await service.import_jsonl(
        _jsonl(
            {
                "name": "张三",
                "current_org": "字节跳动",
                "current_title": "工程师",
                "match_score": 90,
                "score_school": 80,
                "score_company": 95,
                "score_direction": 88,
                "source": "maimai",
            },
            {
                "name": "李四",
                "current_org": "阿里巴巴",
                "current_title": "专家",
                "match_score": 70,
                "source": "maimai",
            },
        ),
        position_id=p1.position_id,
    )
    await service.import_jsonl(
        _jsonl(
            {
                "name": "张三",
                "current_org": "字节跳动",
                "current_title": "工程师",
                "match_score": 60,
                "source": "maimai",
            }
        ),
        position_id=p2.position_id,
    )

    result = await test_session.execute(select(IndustryTalent).where(IndustryTalent.name == "张三"))
    zhangsan = result.scalar_one()
    result2 = await test_session.execute(
        select(IndustryTalent).where(IndustryTalent.name == "李四")
    )
    lisi = result2.scalar_one()
    return p1, p2, zhangsan.talent_id, lisi.talent_id


# ============ Score editing ============


@pytest.mark.asyncio
async def test_patch_candidate_scores(
    admin_client: AsyncClient, test_session: AsyncSession
) -> None:
    """PATCH with score fields updates the link's match_score and sub-scores."""
    p1, _, zhangsan_id, _ = await _seed_candidates(test_session)

    resp = await admin_client.patch(
        f"/api/v1/industry/talents/{zhangsan_id}/positions/{p1.position_id}",
        json={"match_score": 85, "score_school": 70, "score_company": 88, "score_direction": 92},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["match_score"] == 85
    assert data["score_school"] == 70
    assert data["score_company"] == 88
    assert data["score_direction"] == 92


@pytest.mark.asyncio
async def test_patch_scores_range_validation(
    admin_client: AsyncClient, test_session: AsyncSession
) -> None:
    """Score > 100 or < 0 returns 422."""
    p1, _, zhangsan_id, _ = await _seed_candidates(test_session)

    resp = await admin_client.patch(
        f"/api/v1/industry/talents/{zhangsan_id}/positions/{p1.position_id}",
        json={"match_score": 150},
    )
    assert resp.status_code == 422

    resp2 = await admin_client.patch(
        f"/api/v1/industry/talents/{zhangsan_id}/positions/{p1.position_id}",
        json={"score_school": -5},
    )
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_patch_scores_partial(admin_client: AsyncClient, test_session: AsyncSession) -> None:
    """Patching only one sub-score preserves the others."""
    p1, _, zhangsan_id, _ = await _seed_candidates(test_session)

    # Only patch score_school; match_score/score_company/score_direction should stay
    resp = await admin_client.patch(
        f"/api/v1/industry/talents/{zhangsan_id}/positions/{p1.position_id}",
        json={"score_school": 50},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score_school"] == 50
    assert data["match_score"] == 90  # unchanged
    assert data["score_company"] == 95  # unchanged
    assert data["score_direction"] == 88  # unchanged


@pytest.mark.asyncio
async def test_patch_scores_and_status_together(
    admin_client: AsyncClient, test_session: AsyncSession
) -> None:
    """Score and status can be patched in the same request."""
    p1, _, zhangsan_id, _ = await _seed_candidates(test_session)

    resp = await admin_client.patch(
        f"/api/v1/industry/talents/{zhangsan_id}/positions/{p1.position_id}",
        json={"match_score": 77, "status": "connected", "notes": "已联系"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["match_score"] == 77
    assert data["status"] == "connected"


# ============ Remove from position ============


@pytest.mark.asyncio
async def test_remove_talent_from_position(
    admin_client: AsyncClient, test_session: AsyncSession
) -> None:
    """DELETE removes the link; talent is preserved if it has other links."""
    p1, p2, zhangsan_id, _ = await _seed_candidates(test_session)
    # 张三 has links to both p1 and p2 — removing p1 should keep the talent

    resp = await admin_client.delete(
        f"/api/v1/industry/talents/{zhangsan_id}/positions/{p1.position_id}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["link_deleted"] is True
    assert data["orphan_talent_deleted"] is False  # still linked to p2

    # Verify talent still exists
    talent = await test_session.get(IndustryTalent, zhangsan_id)
    assert talent is not None

    # Verify p1 link gone, p2 link remains
    links = await test_session.execute(
        select(IndustryPositionTalent).where(IndustryPositionTalent.talent_id == zhangsan_id)
    )
    remaining = links.scalars().all()
    assert len(remaining) == 1
    assert remaining[0].position_id == p2.position_id


@pytest.mark.asyncio
async def test_remove_position_orphan_talent_cleanup(
    admin_client: AsyncClient, test_session: AsyncSession
) -> None:
    """Removing the last link also cleans up the orphan talent record."""
    p1, _, _, lisi_id = await _seed_candidates(test_session)
    # 李四 only linked to p1 — removing p1 should delete the talent too

    resp = await admin_client.delete(
        f"/api/v1/industry/talents/{lisi_id}/positions/{p1.position_id}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["link_deleted"] is True
    assert data["orphan_talent_deleted"] is True

    # Verify talent gone
    talent = await test_session.get(IndustryTalent, lisi_id)
    assert talent is None


@pytest.mark.asyncio
async def test_remove_requires_super_admin(
    user_client: AsyncClient, test_session: AsyncSession
) -> None:
    """Normal user cannot remove a talent from a position (403)."""
    p1, _, zhangsan_id, _ = await _seed_candidates(test_session)

    resp = await user_client.delete(
        f"/api/v1/industry/talents/{zhangsan_id}/positions/{p1.position_id}"
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_remove_nonexistent_link_returns_404(
    admin_client: AsyncClient, test_session: AsyncSession
) -> None:
    """Deleting a link that doesn't exist returns 404."""
    resp = await admin_client.delete("/api/v1/industry/talents/99999/positions/99999")
    assert resp.status_code == 404
