"""Legacy INDUSTRY_IMPORT_API_KEY migration into shared_api_key."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.models.api_key import ApiKey
from app.domains.shared.services.api_key_service import ApiKeyService
from app.domains.shared.services.config_service import ConfigService

_LEGACY = "legacy-secret-key-123"


@pytest.mark.asyncio
async def test_migration_creates_key_and_clears_sys_config(test_session: AsyncSession) -> None:
    await ConfigService(test_session).set_value("INDUSTRY_IMPORT_API_KEY", _LEGACY)
    await test_session.commit()

    created = await ApiKeyService.migrate_legacy_industry_key(test_session)
    assert created == 1

    records = (await test_session.execute(select(ApiKey))).scalars().all()
    assert len(records) == 1
    assert records[0].scopes == ["industry:write"]
    assert records[0].key_name == "行业导入(迁移)"
    assert records[0].key_prefix == _LEGACY[:8]
    legacy_value = await ConfigService(test_session).get_value(
        "INDUSTRY_IMPORT_API_KEY", use_cache=False
    )
    assert not legacy_value

    # The migrated key verifiably works through the shared auth path
    verified = await ApiKeyService(test_session).verify_key(_LEGACY)
    assert verified is not None


@pytest.mark.asyncio
async def test_migration_idempotent_and_skips_when_absent(
    test_session: AsyncSession,
) -> None:
    # No legacy value configured -> no-op
    assert await ApiKeyService.migrate_legacy_industry_key(test_session) == 0

    await ConfigService(test_session).set_value("INDUSTRY_IMPORT_API_KEY", _LEGACY)
    await test_session.commit()
    assert await ApiKeyService.migrate_legacy_industry_key(test_session) == 1
    # Re-run: legacy config already cleared -> no second row
    assert await ApiKeyService.migrate_legacy_industry_key(test_session) == 0
    records = (await test_session.execute(select(ApiKey))).scalars().all()
    assert len(records) == 1
