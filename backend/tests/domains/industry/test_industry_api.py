"""API tests for industry domain endpoints (positions, talents, import)."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.industry.models.industry import IndustryPosition
from app.domains.industry.services.industry_import_service import IndustryImportService
from app.domains.shared.api.auth import get_current_user
from app.main import app


def _jsonl(*records: dict) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in records)


def _override_user(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 1,
        "username": "tester",
        "role": role,
    }


@pytest.fixture
async def admin_client(client: AsyncClient, test_session: AsyncSession) -> AsyncClient:
    """super_admin client backed by a real user row (created_by FK target)."""
    from app.domains.shared.models.iam import UserAccount

    user = UserAccount(
        username="industry_admin",
        email="industry_admin@example.com",
        password_hash="x",
        role_type="super_admin",
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": user.user_id,
        "username": "industry_admin",
        "role": "super_admin",
    }
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def user_client(client: AsyncClient) -> AsyncClient:
    _override_user("user")
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def positions(test_session: AsyncSession) -> tuple[IndustryPosition, IndustryPosition]:
    p1 = IndustryPosition(
        title="大模型推理工程师",
        department="基础架构",
        tech_direction_codes=["llm", "llm_inference"],
        level_min=19,
        level_max=20,
        status="open",
    )
    p2 = IndustryPosition(
        title="推荐算法工程师",
        tech_direction_codes=["recsys"],
        status="open",
    )
    test_session.add_all([p1, p2])
    await test_session.commit()
    return p1, p2


@pytest.fixture
async def seeded(
    test_session: AsyncSession, positions: tuple[IndustryPosition, IndustryPosition]
) -> tuple[IndustryPosition, IndustryPosition]:
    p1, p2 = positions
    service = IndustryImportService(test_session)
    await service.import_jsonl(
        _jsonl(
            {
                "name": "张三",
                "current_org": "亚马逊云科技",
                "current_title": "应用科学家",
                "degree": "博士",
                "years_of_exp": "10年",
                "location": "北京",
                "source": "maimai",
                "match_score": 98,
                "score_school": 95,
                "score_company": 90,
                "score_direction": 99,
                "match_tags": ["顶级院校", "LLM"],
                "batch": "b1",
            },
            {
                "name": "李四",
                "current_org": "腾讯",
                "current_title": "研究员",
                "source": "maimai",
                "match_score": 72,
            },
        ),
        position_id=p1.position_id,
    )
    # 张三 also matches position 2 with a lower score; 李四 has a linkedin row there
    await service.import_jsonl(
        _jsonl(
            {
                "name": "张三",
                "current_org": "亚马逊云科技",
                "current_title": "应用科学家",
                "match_score": 65,
            },
            {
                "name": "李四",
                "current_org": "腾讯",
                "current_title": "研究员",
                "match_score": 88,
                "source": "linkedin",
            },
        ),
        position_id=p2.position_id,
    )
    return p1, p2


# ============ Position CRUD ============


@pytest.mark.asyncio
async def test_position_crud(admin_client: AsyncClient) -> None:
    payload = {
        "title": "CV 算法工程师",
        "department": "视觉团队",
        "tech_direction_codes": ["cv"],
        "level_min": 17,
        "level_max": 19,
        "jd_text": "负责视觉大模型研发",
    }
    response = await admin_client.post("/api/v1/industry/positions", json=payload)
    assert response.status_code == 200, response.text
    created = response.json()
    assert created["title"] == "CV 算法工程师"
    assert created["status"] == "open"
    assert created["candidate_count"] == 0
    pid = created["position_id"]

    # List with stats
    response = await admin_client.get("/api/v1/industry/positions")
    assert response.status_code == 200
    rows = response.json()
    assert any(r["position_id"] == pid for r in rows)

    # Detail
    response = await admin_client.get(f"/api/v1/industry/positions/{pid}")
    assert response.status_code == 200
    assert response.json()["level_min"] == 17

    # Update: edit + archive (no DELETE endpoint exists)
    response = await admin_client.put(
        f"/api/v1/industry/positions/{pid}",
        json={"status": "archived", "level_max": 21},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "archived"
    assert response.json()["level_max"] == 21

    # Status filter
    response = await admin_client.get("/api/v1/industry/positions", params={"status": "archived"})
    assert [r["position_id"] for r in response.json()] == [pid]

    # Invalid status / level range → 400
    assert (
        await admin_client.put(f"/api/v1/industry/positions/{pid}", json={"status": "bogus"})
    ).status_code == 400
    assert (
        await admin_client.post(
            "/api/v1/industry/positions", json={"title": "X", "level_min": 20, "level_max": 18}
        )
    ).status_code == 400
    assert (await admin_client.get("/api/v1/industry/positions/999999")).status_code == 404


@pytest.mark.asyncio
async def test_position_write_requires_super_admin(user_client: AsyncClient) -> None:
    response = await user_client.post("/api/v1/industry/positions", json={"title": "X"})
    assert response.status_code == 403
    response = await user_client.put("/api/v1/industry/positions/1", json={"title": "Y"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_position_list_candidate_stats(
    admin_client: AsyncClient, seeded: tuple[IndustryPosition, IndustryPosition]
) -> None:
    """F-POS-04: list shows candidate count and average match score."""
    p1, p2 = seeded
    response = await admin_client.get("/api/v1/industry/positions")
    rows = {r["position_id"]: r for r in response.json()}
    assert rows[p1.position_id]["candidate_count"] == 2
    assert rows[p1.position_id]["avg_match_score"] == 85.0  # (98 + 72) / 2
    assert rows[p2.position_id]["candidate_count"] == 2
    assert rows[p2.position_id]["avg_match_score"] == 76.5  # (65 + 88) / 2


# ============ Talent list ============


@pytest.mark.asyncio
async def test_talent_list_default_sort_and_aggregation(
    user_client: AsyncClient, seeded: tuple[IndustryPosition, IndustryPosition]
) -> None:
    response = await user_client.get("/api/v1/industry/talents")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    first, second = data["items"]
    # Default sort: match_score_desc on the best score (98 > 88)
    assert first["name"] == "张三"
    assert first["best_match_score"] == 98
    # Aggregation: both matched positions in one row, no extra queries
    assert len(first["positions"]) == 2
    assert {p["title"] for p in first["positions"]} == {"大模型推理工程师", "推荐算法工程师"}
    assert second["name"] == "李四"
    assert second["best_match_score"] == 88


@pytest.mark.asyncio
async def test_talent_list_filters(
    user_client: AsyncClient, seeded: tuple[IndustryPosition, IndustryPosition]
) -> None:
    p1, p2 = seeded

    async def names(**params) -> list[str]:
        resp = await user_client.get("/api/v1/industry/talents", params=params)
        assert resp.status_code == 200
        return [item["name"] for item in resp.json()["items"]]

    assert await names(keyword="亚马逊") == ["张三"]  # org fuzzy
    assert await names(keyword="科学") == ["张三"]  # title fuzzy
    assert await names(keyword="研究") == ["李四"]  # title fuzzy
    assert await names(position_id=p1.position_id) == ["张三", "李四"]
    assert await names(min_score=90) == ["张三"]
    assert await names(position_id=p2.position_id, min_score=80) == ["李四"]

    # status filter: mark 李四/p2 as contacted first
    talents = (await user_client.get("/api/v1/industry/talents")).json()["items"]
    lisi = next(t for t in talents if t["name"] == "李四")
    resp = await user_client.patch(
        f"/api/v1/industry/talents/{lisi['talent_id']}/positions/{p2.position_id}",
        json={"status": "connected", "touched": True, "notes": "已电话沟通"},
    )
    assert resp.status_code == 200
    assert await names(status="connected") == ["李四"]
    assert await names(status="new") == ["张三", "李四"]  # 李四 still new on p1

    # source_platform / tech_direction
    assert await names(source_platform="linkedin") == ["李四"]
    assert await names(tech_direction="recsys") == ["张三", "李四"]
    assert await names(tech_direction="llm") == ["张三", "李四"]  # both hit p1
    assert await names(tech_direction="cv") == []

    # sort variants (name_asc order is DB-collation dependent — check set only)
    assert await names(sort_by="match_score_asc") == ["李四", "张三"]
    assert sorted(await names(sort_by="name_asc")) == ["张三", "李四"]
    resp = await user_client.get("/api/v1/industry/talents", params={"sort_by": "bogus"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_talent_list_pagination(
    user_client: AsyncClient, seeded: tuple[IndustryPosition, IndustryPosition]
) -> None:
    response = await user_client.get("/api/v1/industry/talents", params={"page": 2, "page_size": 1})
    data = response.json()
    assert data["total"] == 2
    assert data["total_pages"] == 2
    assert len(data["items"]) == 1


# ============ Talent detail & status ============


@pytest.mark.asyncio
async def test_talent_detail_and_positions(
    user_client: AsyncClient, seeded: tuple[IndustryPosition, IndustryPosition]
) -> None:
    p1, _ = seeded
    talents = (await user_client.get("/api/v1/industry/talents")).json()["items"]
    zhangsan = next(t for t in talents if t["name"] == "张三")

    response = await user_client.get(f"/api/v1/industry/talents/{zhangsan['talent_id']}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["degree"] == "博士"
    assert detail["years_of_exp_num"] == 10.0
    assert detail["best_match_score"] == 98
    # Per-position comparison with three-dimension subscores
    matches = {m["position_id"]: m for m in detail["positions"]}
    assert matches[p1.position_id]["match_score"] == 98
    assert matches[p1.position_id]["score_direction"] == 99
    assert matches[p1.position_id]["match_tags"] == ["顶级院校", "LLM"]

    response = await user_client.get(f"/api/v1/industry/talents/{zhangsan['talent_id']}/positions")
    assert response.status_code == 200
    assert len(response.json()) == 2

    assert (await user_client.get("/api/v1/industry/talents/999999")).status_code == 404


@pytest.mark.asyncio
async def test_patch_candidate_status(
    user_client: AsyncClient, seeded: tuple[IndustryPosition, IndustryPosition]
) -> None:
    p1, _ = seeded
    talents = (await user_client.get("/api/v1/industry/talents")).json()["items"]
    zhangsan = next(t for t in talents if t["name"] == "张三")

    response = await user_client.patch(
        f"/api/v1/industry/talents/{zhangsan['talent_id']}/positions/{p1.position_id}",
        json={"status": "connected", "touched": True, "notes": "二面"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connected"
    assert body["touched"] is True
    assert body["notes"] == "二面"
    assert body["match_score"] == 98  # scores untouched by the patch

    # Invalid status → 400; nonexistent link → 404
    assert (
        await user_client.patch(
            f"/api/v1/industry/talents/{zhangsan['talent_id']}/positions/{p1.position_id}",
            json={"status": "bogus"},
        )
    ).status_code == 400
    assert (
        await user_client.patch(
            f"/api/v1/industry/talents/{zhangsan['talent_id']}/positions/999999",
            json={"status": "new"},
        )
    ).status_code == 404


# ============ Import endpoints ============


@pytest.mark.asyncio
async def test_import_upload(
    admin_client: AsyncClient, positions: tuple[IndustryPosition, IndustryPosition]
) -> None:
    p1, _ = positions
    content = _jsonl(
        {"name": "张三", "current_org": "某公司", "match_score": 90},
        {"name": "", "current_org": "无效行"},
    )
    response = await admin_client.post(
        "/api/v1/industry/import/upload",
        data={"position_id": str(p1.position_id), "batch": "api-batch"},
        files={"file": ("candidates.jsonl", content.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["talents_inserted"] == 1
    assert report["links_inserted"] == 1
    assert report["skipped"] == 1

    # Unknown position → 404 before parsing
    response = await admin_client.post(
        "/api/v1/industry/import/upload",
        data={"position_id": "999999"},
        files={"file": ("c.jsonl", content.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_import_upload_requires_super_admin(
    user_client: AsyncClient, positions: tuple[IndustryPosition, IndustryPosition]
) -> None:
    p1, _ = positions
    response = await user_client.post(
        "/api/v1/industry/import/upload",
        data={"position_id": str(p1.position_id)},
        files={"file": ("c.jsonl", b'{"name": "x"}', "text/plain")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_import_push_channel_requires_api_key_config(client: AsyncClient) -> None:
    """The API Key push channel authenticates via shared_api_key.

    An unknown key (no matching shared_api_key row) gets 401. Full
    push-channel coverage (auth success/failure, body parsing, audit) lives
    in test_industry_push_import.py.
    """
    response = await client.post(
        "/api/v1/industry/import?position_id=1",
        content='{"name":"x"}',
        headers={"X-API-Key": "anything"},
    )
    assert response.status_code == 401
