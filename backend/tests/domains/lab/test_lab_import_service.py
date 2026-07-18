"""Tests for LabImportService — JSONL parsing and per-lab full replace."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab.models.lab_talent import LabTalent
from app.domains.lab.services.lab_import_service import LabImportService
from app.domains.lab.services.lab_talent_service import LabTalentService


def _person(name: str, parent_lab: str = "Stanford AI Lab", **kwargs) -> str:
    """Build one JSONL line for a person."""
    record = {
        "name": name,
        "role_section": kwargs.get("role_section", "PhD Students"),
        "lab_name": kwargs.get("lab_name", "Stanford NLP Group"),
        "parent_lab": parent_lab,
        "source_url": kwargs.get("source_url", "https://nlp.stanford.edu/people/"),
        "collected_at": kwargs.get("collected_at", "2026-07-02T10:00:00Z"),
    }
    record.update({k: v for k, v in kwargs.items() if k not in record})
    return json.dumps(record)


class TestLabImportService:
    """Integration tests against a real test_session (PostgreSQL)."""

    @pytest.mark.asyncio
    async def test_import_parses_and_inserts(self, test_session: AsyncSession):
        """A clean JSONL imports all valid rows and reports correct counts."""
        jsonl = "\n".join(
            [
                _person("Alice"),
                _person("Bob", role_section="Faculty"),
                _person("Carol", role_section="Master Students"),
            ]
        )
        service = LabImportService(test_session)
        report = await service.import_jsonl(jsonl, "Stanford AI Lab")

        assert report.parent_lab == "Stanford AI Lab"
        assert report.total_lines == 3
        assert report.total_parsed == 3
        assert report.inserted == 3
        assert report.skipped == 0

    @pytest.mark.asyncio
    async def test_import_skips_invalid_lines(self, test_session: AsyncSession):
        """Invalid JSON and missing-name rows are skipped, not fatal."""
        jsonl = "\n".join(
            [
                "not valid json",
                _person(""),  # empty name → skipped
                json.dumps({"role_section": "Faculty"}),  # missing name key
                _person("Dave"),  # valid
            ]
        )
        service = LabImportService(test_session)
        report = await service.import_jsonl(jsonl, "Stanford AI Lab")

        assert report.total_parsed == 1
        assert report.inserted == 1
        assert report.skipped == 3
        assert len(report.skip_reasons) == 3

    @pytest.mark.asyncio
    async def test_import_full_replace_deletes_old(self, test_session: AsyncSession):
        """Re-importing the same parent_lab replaces, not appends."""
        service = LabImportService(test_session)

        # First import: 2 people
        await service.import_jsonl(
            "\n".join([_person("Eve"), _person("Frank")]),
            "Stanford AI Lab",
        )
        count_after_first = await test_session.scalar(
            select(func.count())
            .select_from(LabTalent)
            .where(LabTalent.parent_lab == "Stanford AI Lab")
        )
        assert count_after_first == 2

        # Second import: 1 different person → should end with 1, not 3
        await service.import_jsonl(_person("Grace"), "Stanford AI Lab")
        count_after_second = await test_session.scalar(
            select(func.count())
            .select_from(LabTalent)
            .where(LabTalent.parent_lab == "Stanford AI Lab")
        )
        assert count_after_second == 1

        # Eve and Frank gone, Grace present
        names = {
            r[0]
            for r in (
                await test_session.execute(
                    select(LabTalent.name).where(LabTalent.parent_lab == "Stanford AI Lab")
                )
            ).all()
        }
        assert names == {"Grace"}

    @pytest.mark.asyncio
    async def test_import_does_not_touch_other_labs(self, test_session: AsyncSession):
        """Importing lab A must not delete lab B's data."""
        service = LabImportService(test_session)
        await service.import_jsonl(_person("Hank", parent_lab="MIT CSAIL"), "MIT CSAIL")
        await service.import_jsonl(_person("Ivy"), "Stanford AI Lab")

        mit_count = await test_session.scalar(
            select(func.count()).select_from(LabTalent).where(LabTalent.parent_lab == "MIT CSAIL")
        )
        assert mit_count == 1  # MIT untouched by Stanford import

    @pytest.mark.asyncio
    async def test_role_mapping_applied_during_import(self, test_session: AsyncSession):
        """Imported rows have role_type/academic_level mapped from role_section."""
        jsonl = "\n".join(
            [
                _person("PhD Person", role_section="PhD Students"),
                _person("Master Person", role_section="Master Students"),
                _person("Prof Person", role_section="Faculty"),
            ]
        )
        service = LabImportService(test_session)
        await service.import_jsonl(jsonl, "Stanford AI Lab")

        talent_service = LabTalentService(test_session)
        items, _ = await talent_service.list_talents(parent_lab="Stanford AI Lab", page_size=50)
        by_name = {i.name: i for i in items}

        assert by_name["PhD Person"].role_type == "student"
        assert by_name["PhD Person"].academic_level == "phd"
        assert by_name["Master Person"].academic_level == "master"
        assert by_name["Prof Person"].role_type == "professor"
        assert by_name["Prof Person"].academic_level is None

    @pytest.mark.asyncio
    async def test_import_lists_research_areas(self, test_session: AsyncSession):
        """research_areas array survives the round-trip."""
        jsonl = _person("Jen", research_areas=["NLP", "Machine Learning"])
        service = LabImportService(test_session)
        await service.import_jsonl(jsonl, "Stanford AI Lab")

        talent_service = LabTalentService(test_session)
        items, _ = await talent_service.list_talents(parent_lab="Stanford AI Lab")
        assert items[0].research_areas == ["NLP", "Machine Learning"]

    @pytest.mark.asyncio
    async def test_import_social_links_cleaned(self, test_session: AsyncSession):
        """social_links keeps only valid http(s) entries, lowercases platform keys."""
        jsonl = _person(
            "Kate",
            social_links={
                "LinkedIn": "https://www.linkedin.com/in/kate",
                "github": "https://github.com/kate",
                "bad": "not-a-url",
                "": "https://empty-key.example.com",
                "broken": None,
            },
        )
        service = LabImportService(test_session)
        await service.import_jsonl(jsonl, "Stanford AI Lab")

        result = await test_session.execute(select(LabTalent).where(LabTalent.name == "Kate"))
        talent = result.scalar_one()
        assert talent.social_links == {
            "linkedin": "https://www.linkedin.com/in/kate",
            "github": "https://github.com/kate",
        }

    @pytest.mark.asyncio
    async def test_import_social_links_defaults_to_empty(self, test_session: AsyncSession):
        """Records without social_links import with an empty dict, not NULL/None."""
        jsonl = _person("Leo")
        service = LabImportService(test_session)
        await service.import_jsonl(jsonl, "Stanford AI Lab")

        result = await test_session.execute(select(LabTalent).where(LabTalent.name == "Leo"))
        talent = result.scalar_one()
        assert talent.social_links == {}
