"""Open-API import endpoints: scope gates + happy paths for three domains."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.industry.models.industry import IndustryPosition
from app.domains.shared.services.api_key_service import ApiKeyService

_MAX_BYTES = 20 * 1024 * 1024

_LAB_JSONL = "\n".join(
    json.dumps(r, ensure_ascii=False)
    for r in [
        {"name": "开放导入教授", "parent_lab": "OpenAPI Lab", "role_type": "faculty"},
        {"name": "开放导入学生", "parent_lab": "OpenAPI Lab", "role_type": "phd"},
    ]
)

_COMP_RECORDS = [
    {"type": "meta", "source_code": "codeforces", "contest_external_id": "9999", "schema_version": "1.0"},
    {"type": "series", "code": "codeforces", "name": "Codeforces"},
    {
        "type": "contest",
        "external_id": "9999",
        "name": "OpenAPI Test Round",
        "source_url": "https://codeforces.com/contest/9999",
    },
    {
        "type": "person",
        "handle": "openapi_tester",
        "result": {"rank": 1, "award": "gold"},
        "real_name": "开放导入选手",
        "country_code": "CN",
        "rank_title": "master",
    },
]

_INDUSTRY_JSONL = json.dumps(
    {
        "name": "开放导入候选人",
        "current_org": "某公司",
        "current_title": "工程师",
        "source": "maimai",
        "match_score": 85,
    },
    ensure_ascii=False,
)


async def _make_key(session: AsyncSession, scopes: list[str]) -> str:
    created = await ApiKeyService(session).create_key(key_name="import", scopes=scopes, created_by=1)
    await session.commit()
    return created["key"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url,scope,body",
    [
        ("/api/v1/open-api/industry/import?position_id=1", "industry:write", _INDUSTRY_JSONL),
        ("/api/v1/open-api/competition/import", "competition:write", "[]"),
        ("/api/v1/open-api/lab/import?parent_lab=X", "lab:write", "[]"),
    ],
)
async def test_import_requires_write_scope(
    client: AsyncClient, test_session: AsyncSession, url: str, scope: str, body: str
) -> None:
    r = await client.post(url, content=body)
    assert r.status_code == 401

    read_only = await _make_key(test_session, [scope.replace(":write", ":read")])
    r = await client.post(url, content=body, headers={"X-API-Key": read_only})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_lab_import_happy_path(client: AsyncClient, test_session: AsyncSession) -> None:
    key = await _make_key(test_session, ["lab:write"])
    r = await client.post(
        "/api/v1/open-api/lab/import",
        params={"parent_lab": "OpenAPI Lab"},
        content=_LAB_JSONL,
        headers={"X-API-Key": key, "Content-Type": "application/x-ndjson"},
    )
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["total_parsed"] == 2
    assert report["parent_lab"] == "OpenAPI Lab"


@pytest.mark.asyncio
async def test_competition_import_happy_path(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    key = await _make_key(test_session, ["competition:write"])
    content = "\n".join(json.dumps(r, ensure_ascii=False) for r in _COMP_RECORDS)
    r = await client.post(
        "/api/v1/open-api/competition/import",
        content=content,
        headers={"X-API-Key": key, "Content-Type": "application/x-ndjson"},
    )
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["persons_upserted"] >= 1
    assert report["contest_name"] == "OpenAPI Test Round"


@pytest.mark.asyncio
async def test_industry_import_happy_path(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    pos = IndustryPosition(title="开放导入岗位", status="open")
    test_session.add(pos)
    await test_session.commit()

    key = await _make_key(test_session, ["industry:write"])
    r = await client.post(
        "/api/v1/open-api/industry/import",
        params={"position_id": pos.position_id, "batch": "openapi-smoke"},
        content=_INDUSTRY_JSONL,
        headers={"X-API-Key": key, "Content-Type": "application/x-ndjson"},
    )
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["talents_inserted"] + report["talents_updated"] >= 1
    assert report["aborted"] is False


@pytest.mark.asyncio
async def test_import_invalid_utf8_400(client: AsyncClient, test_session: AsyncSession) -> None:
    key = await _make_key(test_session, ["lab:write"])
    r = await client.post(
        "/api/v1/open-api/lab/import",
        params={"parent_lab": "X"},
        content=b"\xff\xfe\x00broken",
        headers={"X-API-Key": key},
    )
    assert r.status_code == 400
