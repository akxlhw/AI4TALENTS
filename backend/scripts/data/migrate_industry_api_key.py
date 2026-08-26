"""CLI shell for the legacy industry API key migration.

The actual logic lives on ApiKeyService.migrate_legacy_industry_key so the
app itself never imports from the scripts tree. Run manually:
    cd backend && uv run python -m scripts.data.migrate_industry_api_key
"""

from __future__ import annotations

import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.domains.shared.services.api_key_service import ApiKeyService

logger = logging.getLogger(__name__)


async def main() -> None:
    async with AsyncSessionLocal() as session:
        created = await ApiKeyService.migrate_legacy_industry_key(session)
    logger.info(f"Industry API key migration done (rows created: {created})")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
