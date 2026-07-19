"""API tests for competition query endpoints (M1.4)."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.competition.services.comp_import_service import CompImportService
from app.domains.shared.api.auth import get_current_user
from app.main import app


def _jsonl(*records: dict) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in records)


SAMPLE_JSONL = _jsonl(
    {
        "type": "meta",
        "schema_version": "1.0",
        "source_code": "codeforces",
        "contest_external_id": "1950",
        "crawler": "comp-talent-crawler",
        "crawler_version": "1.0.0",
        "collected_at": "2026-07-19T08:00:00Z",
    },
    {"type": "series", "code": "codeforces", "name": "Codeforces"},
    {
        "type": "contest",
        "external_id": "1950",
        "name": "Codeforces Round 951 (Div. 1)",
        "start_time": "2024-05-30T14:35:00Z",
        "season": "2024",
        "status": "finished",
        "source_url": "https://codeforces.com/contest/1950",
    },
    {
        "type": "person",
        "handle": "tourist",
        "real_name": "Gennady Korotkevich",
        "school": "ITMO University",
        "country_code": "BY",
        "rating": 3948,
        "max_rating": 3979,
        "rank_title": "legendary grandmaster",
        "result": {"rank": 1, "rating_before": 3904, "rating_after": 3948, "award": "gold"},
    },
    {
        "type": "person",
        "handle": "jiangly",
        "school": "Zhejiang University",
        "country_code": "CN",
        "rating": 3756,
        "rank_title": "international grandmaster",
        "result": {"rank": 3, "rating_before": 3711, "rating_after": 3756, "award": "bronze"},
    },
)


@pytest.fixture
async def user_client(client: AsyncClient) -> AsyncClient:
    """HTTP client with an authenticated user dependency override."""
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 1,
        "username": "tester",
        "role": "user",
    }
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def seeded(test_session: AsyncSession) -> None:
    await CompImportService(test_session).import_jsonl(SAMPLE_JSONL)


@pytest.mark.asyncio
async def test_endpoints_allow_anonymous_read(client: AsyncClient, seeded: None) -> None:
    """Read endpoints follow the project convention: get_current_user is
    auth-optional (returns None without a token), same as the lab domain —
    frontend routes are gated by ProtectedRoute instead."""
    for path in (
        "/api/v1/comp/talents",
        "/api/v1/comp/contests",
        "/api/v1/comp/overview",
        "/api/v1/comp/series",
    ):
        response = await client.get(path)
        assert response.status_code == 200, path


@pytest.mark.asyncio
async def test_list_talents_filter_and_sort(user_client: AsyncClient, seeded: None) -> None:
    response = await user_client.get("/api/v1/comp/talents", params={"sort_by": "rating_desc"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["items"][0]["handle"] == "tourist"  # rating_desc

    response = await user_client.get("/api/v1/comp/talents", params={"keyword": "gennady"})
    assert response.json()["total"] == 1  # real_name fuzzy

    response = await user_client.get("/api/v1/comp/talents", params={"country_code": "CN"})
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["handle"] == "jiangly"

    response = await user_client.get("/api/v1/comp/talents", params={"min_rating": 3900})
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_talent_detail_and_404(user_client: AsyncClient, seeded: None) -> None:
    items = (await user_client.get("/api/v1/comp/talents")).json()["items"]
    talent_id = items[0]["talent_id"]

    response = await user_client.get(f"/api/v1/comp/talents/{talent_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["handle"] == "tourist"
    assert data["rank_title"] == "legendary grandmaster"
    assert len(data["results"]) == 1
    assert data["results"][0]["contest_name"] == "Codeforces Round 951 (Div. 1)"
    assert data["results"][0]["award"] == "gold"

    assert (await user_client.get("/api/v1/comp/talents/999999")).status_code == 404


@pytest.mark.asyncio
async def test_contests_list_and_detail(user_client: AsyncClient, seeded: None) -> None:
    response = await user_client.get("/api/v1/comp/contests")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    contest_id = data["items"][0]["contest_id"]
    assert data["items"][0]["results_count"] == 2

    response = await user_client.get(f"/api/v1/comp/contests/{contest_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["name"] == "Codeforces Round 951 (Div. 1)"
    assert len(detail["results"]) == 2
    assert detail["results"][0]["handle"] == "tourist"  # rank asc
    assert detail["results"][0]["rating_after"] == 3948

    assert (await user_client.get("/api/v1/comp/contests/999999")).status_code == 404


@pytest.mark.asyncio
async def test_overview_and_series(user_client: AsyncClient, seeded: None) -> None:
    response = await user_client.get("/api/v1/comp/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_talents"] == 2
    assert data["total_contests"] == 1
    assert data["total_medalists"] == 1
    assert data["total_countries"] == 2
    assert data["top_talents"][0]["handle"] == "tourist"
    assert data["recent_contests"][0]["name"] == "Codeforces Round 951 (Div. 1)"

    response = await user_client.get("/api/v1/comp/series")
    assert response.status_code == 200
    rows = response.json()
    cf = next(r for r in rows if r["code"] == "codeforces")
    assert cf["talents_count"] == 2
    assert cf["contests_count"] == 1
