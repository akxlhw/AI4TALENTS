"""Regression tests: static routes must be registered before /{pool_id}.

FastAPI matches routes in registration order. GET /talent-pools/{pool_id}
was registered before GET /talent-pools/followup-statuses, so the static
path matched the int-validated pool_id parameter and 422'd — surfacing as
"加载跟进状态失败" on the favorites page.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_followup_statuses_route_not_shadowed(client: AsyncClient) -> None:
    """GET /followup-statuses must return the option list, not a 422 from
    pool_id validation."""
    response = await client.get("/api/v1/talent-pools/followup-statuses")
    assert response.status_code == 200
    options = response.json()
    assert isinstance(options, list) and options
    assert any(opt["value"] == "new_found" for opt in options)


@pytest.mark.asyncio
async def test_get_pool_by_id_still_resolves(client: AsyncClient) -> None:
    """The dynamic /{pool_id} route keeps working after the reordering:
    a valid int id reaches the auth gate (401), an invalid one would 422."""
    response = await client.get("/api/v1/talent-pools/999999")
    assert response.status_code == 401
