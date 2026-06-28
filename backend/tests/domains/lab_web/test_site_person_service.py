"""Integration tests for LWSitePersonService (raw -> core_talent, source_type=lab_web_site)."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.domains.academic.models.talent import Talent
from app.domains.lab_web.models.lab_web import LWRawPerson
from app.domains.lab_web.services.lw_site_person_service import LWSitePersonService
from app.domains.shared.models.enums import RoleType, SourceType

pytestmark = pytest.mark.integration


async def _make_site_raw(lab_id: int, name: str, role_section: str, content_hash: str, **extra):
    return LWRawPerson(
        lab_id=lab_id,
        name_raw=name,
        content_hash=content_hash,
        raw_data={
            "site_code": "test_site",
            "parent_lab_code": "stanford_sail",
            "role_section": role_section,
            "department": extra.get("department"),
            "homepage": extra.get("homepage"),
            "source_type": "lab_web_site",
        },
    )


async def test_sync_creates_core_talent_with_role(test_session, sample_lab):
    svc = LWSitePersonService(test_session)
    raw = await _make_site_raw(sample_lab.lab_id, "Alice Lee", "PhD Students", "sh1")
    result = await svc.sync_to_core_talent([raw])
    assert result.synced == 1
    rows = (await test_session.execute(select(Talent))).scalars().all()
    assert len(rows) == 1
    t = rows[0]
    assert t.name == "Alice Lee"
    assert t.source_type == SourceType.LAB_WEB_SITE.value
    assert t.role_type == RoleType.STUDENT.value
    assert t.role_confidence == 1.0
    assert t.extra_data["role_section_raw"] == "PhD Students"


async def test_sync_upsert_no_duplicate(test_session, sample_lab):
    svc = LWSitePersonService(test_session)
    raw = await _make_site_raw(sample_lab.lab_id, "Alice", "Faculty", "sh1")
    await svc.sync_to_core_talent([raw])
    raw2 = await _make_site_raw(
        sample_lab.lab_id, "Alice", "Faculty", "sh1", homepage="https://new.example"
    )
    await svc.sync_to_core_talent([raw2])
    rows = (await test_session.execute(select(Talent))).scalars().all()
    assert len(rows) == 1  # upsert, not insert
    assert rows[0].extra_data.get("homepage") == "https://new.example"


async def test_sync_isolates_from_v1_and_openalex(test_session, sample_lab):
    existing = Talent(
        name="Other",
        source_type=SourceType.OPENALEX.value,
        source_record_id="oa-1",
        role_type=RoleType.UNKNOWN.value,
        is_visible=True,
    )
    test_session.add(existing)
    await test_session.commit()
    svc = LWSitePersonService(test_session)
    raw = await _make_site_raw(sample_lab.lab_id, "Alice", "Faculty", "site-sh1")
    await svc.sync_to_core_talent([raw])
    rows = (await test_session.execute(select(Talent))).scalars().all()
    assert len(rows) == 2
    oa = [r for r in rows if r.source_type == SourceType.OPENALEX.value][0]
    assert oa.name == "Other"  # untouched
    site = [r for r in rows if r.source_type == SourceType.LAB_WEB_SITE.value][0]
    assert site.name == "Alice"
