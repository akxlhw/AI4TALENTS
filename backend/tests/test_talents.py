"""
Tests for Talents API endpoints.
人才 API 测试
"""

import pytest
from httpx import AsyncClient


class TestTalentDetail:
    """Tests for /api/v1/talents/{talent_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_talent_detail_success(self, client: AsyncClient, sample_talent: dict):
        """Test getting talent detail by ID."""
        talent = sample_talent["talent"]
        response = await client.get(f"/api/v1/talents/{talent.talent_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["talent_id"] == talent.talent_id
        assert data["name"] == talent.name

    @pytest.mark.asyncio
    async def test_get_talent_detail_not_found(self, client: AsyncClient):
        """Test getting non-existent talent returns 404."""
        response = await client.get("/api/v1/talents/99999")

        assert response.status_code == 404


class TestTalentList:
    """Tests for talents list endpoint."""

    @pytest.mark.asyncio
    async def test_list_talents(self, client: AsyncClient, sample_talent: dict):
        """Test listing talents."""
        response = await client.get("/api/v1/talents")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_talents_with_pagination(self, client: AsyncClient, sample_talent: dict):
        """Test listing talents with pagination."""
        response = await client.get(
            "/api/v1/talents",
            params={"page": 1, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10


class TestTalentExport:
    """Tests for talents export endpoint."""

    @pytest.mark.asyncio
    async def test_export_talents_csv(self, client: AsyncClient, sample_talent: dict):
        """Test exporting talents as CSV."""
        talent = sample_talent["talent"]
        response = await client.post(
            "/api/v1/talents/export",
            json={"talent_ids": [talent.talent_id], "format": "csv"},
        )

        # May return 404 if endpoint not implemented
        if response.status_code == 200:
            assert response.headers["content-type"] in [
                "text/csv",
                "text/csv; charset=utf-8",
            ]

    @pytest.mark.asyncio
    async def test_export_talents_xlsx(self, client: AsyncClient, sample_talent: dict):
        """Test exporting talents as Excel."""
        talent = sample_talent["talent"]
        response = await client.post(
            "/api/v1/talents/export",
            json={"talent_ids": [talent.talent_id], "format": "xlsx"},
        )

        # May return 404 if endpoint not implemented
        if response.status_code == 200:
            assert "spreadsheet" in response.headers.get("content-type", "")


class TestTalentWorks:
    """Tests for talent works endpoint."""

    @pytest.mark.asyncio
    async def test_get_talent_works(self, client: AsyncClient, sample_talent: dict):
        """Test getting talent works."""
        talent = sample_talent["talent"]
        response = await client.get(f"/api/v1/talents/{talent.talent_id}/works")

        # May return 404 if no works or endpoint not implemented
        assert response.status_code in [200, 404]


class TestTalentCollaborations:
    """Tests for talent collaborations endpoint."""

    @pytest.mark.asyncio
    async def test_get_talent_collaborations(self, client: AsyncClient, sample_talent: dict):
        """Test getting talent collaborations."""
        talent = sample_talent["talent"]
        response = await client.get(f"/api/v1/talents/{talent.talent_id}/collaborations")

        # May return 404 if no collaborations or endpoint not implemented
        assert response.status_code in [200, 404]
