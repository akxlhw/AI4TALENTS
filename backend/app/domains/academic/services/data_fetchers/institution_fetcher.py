"""Institution fetcher for the OpenAlex raw data layer.

Split from the original data_fetchers.py monolith.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.academic.models.raw_data import RawInstitution
from app.domains.academic.repositories.raw_data_repository import RawInstitutionRepository
from app.domains.academic.services.common.openalex_utils import (
    OPENALEX_API_BASE,
    REQUEST_DELAY,
    extract_short_id,
)
from app.domains.academic.services.common.progress import FetchProgress
from app.domains.academic.services.data_fetchers.common import (
    OpenAlexClient,
    RetryableError,
    _openalex_fetcher_breaker,
    _rate_limited_error,
    _record_upstream,
    with_retry,
)

logger = logging.getLogger(__name__)


class InstitutionFetcher:
    """Fetcher for institutions from OpenAlex"""

    def __init__(self, session: AsyncSession, client: OpenAlexClient | None = None):
        self.session = session
        self.client = client or OpenAlexClient()
        self.repo = RawInstitutionRepository(session)

    @with_retry(max_attempts=3, max_wait=30.0)
    async def _fetch_batch_with_retry(
        self,
        http_session: aiohttp.ClientSession,
        url: str,
        params: dict,
        headers: dict,
        proxy: str | None = None,
    ) -> dict:
        """带重试和熔断保护的批量获取"""

        async def _do_fetch() -> dict:
            started = time.monotonic()
            async with http_session.get(
                url, params=params, headers=headers, proxy=proxy
            ) as response:
                _record_upstream(response.status, started)
                if response.status == 429:
                    raise _rate_limited_error(response)
                if response.status >= 500:
                    raise RetryableError(f"Server error (HTTP {response.status})")
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                return await response.json()

        if not settings.CIRCUIT_BREAKER_ENABLED:
            return await _do_fetch()
        return await _openalex_fetcher_breaker.call(_do_fetch)

    async def fetch_institutions_by_ids(
        self,
        institution_ids: list[str],
        task_id: int | None = None,
        progress_callback: callable | None = None,
    ) -> FetchProgress:
        """Fetch institutions by their OpenAlex IDs"""
        progress = FetchProgress()
        progress.total = len(institution_ids)
        progress.current_step = "Fetching institutions from OpenAlex"

        logger.info(f"开始获取机构数据: 共 {len(institution_ids)} 个机构")

        # Find which institutions are already in database
        missing_ids = await self.repo.get_missing_ids(institution_ids)
        progress.current_step = f"Fetching {len(missing_ids)} new institutions"

        logger.info(
            f"其中 {len(missing_ids)} 个需要从 API 获取，{len(institution_ids) - len(missing_ids)} 个已存在"
        )

        # Determine proxy for OpenAlex API
        openalex_url = f"{OPENALEX_API_BASE}/institutions"
        proxy = self.client.get_proxy_for_request(openalex_url)
        async with self.client.create_session() as http_session:
            batch_size = min(settings.EMBEDDING_BATCH_SIZE, 50)
            total_batches = (len(missing_ids) + batch_size - 1) // batch_size

            for i in range(0, len(missing_ids), batch_size):
                batch = missing_ids[i : i + batch_size]
                batch_num = i // batch_size + 1

                try:
                    url = f"{OPENALEX_API_BASE}/institutions"
                    params = {"filter": f"openalex:{'|'.join(batch)}", "per_page": 50}

                    headers = {}
                    if self.client.email:
                        headers["mailto"] = self.client.email

                    data = await self._fetch_batch_with_retry(
                        http_session, url, params, headers, proxy
                    )

                    institutions = data.get("results", [])
                    batch_insts: list[RawInstitution] = []
                    for inst_data in institutions:
                        try:
                            raw_inst = RawInstitution(
                                openalex_institution_id=extract_short_id(inst_data.get("id", "")),
                                raw_json=json.dumps(inst_data),
                                display_name=inst_data.get("display_name"),
                                country_code=inst_data.get("country_code"),
                                country_name=inst_data.get("geo", {}).get("country_name"),
                                ror=inst_data.get("ror"),
                                type=inst_data.get("type"),
                                fetch_task_id=task_id,
                                fetched_at=datetime.now(timezone.utc).replace(tzinfo=None),
                            )
                            batch_insts.append(raw_inst)
                            progress.fetched += 1
                        except Exception as e:
                            logger.warning(f"解析机构数据失败: {e}")
                            progress.failed += 1

                    if batch_insts:
                        await self.repo.batch_upsert(batch_insts)
                        batch_insts = []

                    # 每 5 批提交一次，减少锁持有时间
                    if batch_num % 5 == 0:
                        await self.session.commit()
                        logger.info(
                            f"机构获取进度: {batch_num}/{total_batches} 批次, 已获取 {progress.fetched} 个"
                        )

                except Exception as e:
                    logger.error(f"批次 {batch_num} 获取失败: {e}")
                    progress.failed += len(batch)

                if progress_callback:
                    progress_callback(progress)

                await asyncio.sleep(REQUEST_DELAY)

        logger.info(f"机构获取完成: 共 {progress.fetched} 个, 失败 {progress.failed} 个")
        return progress
