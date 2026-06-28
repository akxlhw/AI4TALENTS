"""Integration tests for LWPersonService (raw -> core_talent sync)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.domains.academic.models.talent import Talent
from app.domains.lab_web.models.lab_web import LWRawPerson
from app.domains.lab_web.services.lw_person_service import LWPersonService
from app.domains.shared.models.enums import RoleType, SourceType

pytestmark = pytest.mark.integration


async def _make_raw(lab_id: int, name: str, title: str, content_hash: str, **extra):
    row = LWRawPerson(
        lab_id=lab_id,
        name_raw=name,
        title_raw=title,
        content_hash=content_hash,
        raw_data={"title_raw": title},
        **extra,
    )
    return row


async def test_sync_creates_core_talent(test_session, sample_lab):
    svc = LWPersonService(test_session)
    raw = await _make_raw(sample_lab.lab_id, "John Smith", "Assistant Professor", "h1")
    result = await svc.sync_to_core_talent([raw], sample_lab)
    assert result.synced == 1

    rows = (await test_session.execute(select(Talent))).scalars().all()
    assert len(rows) == 1
    t = rows[0]
    assert t.name == "John Smith"
    assert t.source_type == SourceType.LAB_WEB.value
    assert t.source_record_id == "h1"
    assert t.role_type == RoleType.PROFESSOR.value
    assert t.lab_name == "Test Lab"
    assert t.department_name == "Test University"
    assert t.current_title == "Assistant Professor"
    assert t.is_visible is True


async def test_sync_upsert_does_not_duplicate(test_session, sample_lab):
    svc = LWPersonService(test_session)
    raw = await _make_raw(sample_lab.lab_id, "John Smith", "PhD Candidate", "h1")
    await svc.sync_to_core_talent([raw], sample_lab)
    # Re-sync with same hash but updated title -> upsert, not insert.
    raw2 = await _make_raw(sample_lab.lab_id, "John Smith", "PhD Candidate (A)", "h1")
    await svc.sync_to_core_talent([raw2], sample_lab)
    rows = (await test_session.execute(select(Talent))).scalars().all()
    assert len(rows) == 1
    assert rows[0].current_title == "PhD Candidate (A)"


async def test_sync_isolates_from_openalex_records(test_session, sample_lab):
    """lab_web sync must never touch openalex-sourced talents.

    core_talent.source_record_id has a GLOBAL unique constraint, so different
    sources must use distinct ids (real data does: content_hash vs OpenAlex
    numeric id). This test verifies the lab_web upsert's WHERE source_type
    scoping: a lab_web person with the SAME name as an existing openalex person
    is inserted as a SEPARATE row, and the openalex row is left untouched.
    """
    # Pre-existing openalex talent (distinct source_record_id, same name).
    existing = Talent(
        name="John Smith",
        source_type=SourceType.OPENALEX.value,
        source_record_id="openalex-999",
        role_type=RoleType.UNKNOWN.value,
        is_visible=True,
    )
    test_session.add(existing)
    await test_session.commit()

    svc = LWPersonService(test_session)
    raw = await _make_raw(sample_lab.lab_id, "John Smith", "Professor", "labweb-h1")
    await svc.sync_to_core_talent([raw], sample_lab)

    rows = (await test_session.execute(select(Talent))).scalars().all()
    assert len(rows) == 2  # openalex one untouched + new lab_web one
    oa = [r for r in rows if r.source_type == SourceType.OPENALEX.value][0]
    # openalex row unchanged: still UNKNOWN role (lab_web would set PROFESSOR)
    assert oa.role_type == RoleType.UNKNOWN.value
    assert oa.source_record_id == "openalex-999"
    lw = [r for r in rows if r.source_type == SourceType.LAB_WEB.value][0]
    assert lw.source_record_id == "labweb-h1"
    assert lw.role_type == RoleType.PROFESSOR.value
