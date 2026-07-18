"""Tests for LabTalentService detail serialization (LinkedIn search-URL fallback)."""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab.services.lab_import_service import LabImportService
from app.domains.lab.services.lab_talent_service import (
    LabTalentService,
    _linkedin_search_url,
)


def _person(name: str, parent_lab: str = "Princeton CS / ML", **kwargs) -> str:
    record = {
        "name": name,
        "role_section": kwargs.get("role_section", "PhD Students"),
        "lab_name": kwargs.get("lab_name", "Princeton CS / ML"),
        "parent_lab": parent_lab,
        "source_url": kwargs.get("source_url", "https://www.cs.princeton.edu/people/grad"),
        "collected_at": kwargs.get("collected_at", "2026-07-17T10:00:00Z"),
    }
    record.update({k: v for k, v in kwargs.items() if k not in record})
    return json.dumps(record)


class TestLinkedinSearchUrl:
    def test_combines_quoted_name_affiliation_keyword(self):
        url = _linkedin_search_url("Joshua Aduol", "Princeton CS / ML")
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "www.google.com"
        assert parsed.path == "/search"
        q = parse_qs(parsed.query)["q"][0]
        assert '"Joshua Aduol"' in q
        assert "Princeton CS / ML" in q
        assert "linkedin" in q

    def test_empty_affiliation_omitted(self):
        url = _linkedin_search_url("Joshua Aduol", "")
        q = parse_qs(urlparse(url).query)["q"][0]
        assert q == '"Joshua Aduol" linkedin'


class TestGetTalentDetailLinkedinFallback:
    @pytest.mark.asyncio
    async def test_fallback_search_url_when_no_real_link(self, test_session: AsyncSession):
        """Detail DTO gets a Google search URL when crawler found no LinkedIn."""
        await LabImportService(test_session).import_jsonl(
            _person("Joshua Aduol"), "Princeton CS / ML"
        )
        service = LabTalentService(test_session)
        items, _ = await service.list_talents(parent_lab="Princeton CS / ML")
        detail = await service.get_talent_detail(items[0].talent_id)

        link = detail.social_links["linkedin"]
        assert link.startswith("https://www.google.com/search?q=")
        q = parse_qs(urlparse(link).query)["q"][0]
        assert '"Joshua Aduol"' in q
        assert "Princeton CS / ML" in q

    @pytest.mark.asyncio
    async def test_real_linkedin_takes_precedence(self, test_session: AsyncSession):
        """A crawler-found real LinkedIn URL is kept as-is, never replaced."""
        real = "https://www.linkedin.com/in/jaduol"
        await LabImportService(test_session).import_jsonl(
            _person(
                "Joshua Aduol",
                social_links={"linkedin": real, "github": "https://github.com/jaduol"},
            ),
            "Princeton CS / ML",
        )
        service = LabTalentService(test_session)
        items, _ = await service.list_talents(parent_lab="Princeton CS / ML")
        detail = await service.get_talent_detail(items[0].talent_id)

        assert detail.social_links["linkedin"] == real
        assert detail.social_links["github"] == "https://github.com/jaduol"
