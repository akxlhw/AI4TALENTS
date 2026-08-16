"""Author fetcher for the OpenAlex raw data layer.

Split from the original data_fetchers.py monolith.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.academic.models.raw_data import RawAuthor
from app.domains.academic.repositories.raw_data_repository import RawAuthorRepository
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


def extract_institutions(author_data: dict) -> dict:
    """
    Extract primary education and company institutions from OpenAlex author data.

    Selection strategy: Choose the institution with the most publication years
    (affiliations.years count) for each type.

    Args:
        author_data: OpenAlex author JSON data

    Returns:
        dict with keys:
            - primary_education: {'id': str, 'name': str} or None
            - primary_company: {'id': str, 'name': str} or None
    """
    result = {
        "primary_education": None,
        "primary_company": None,
    }

    affiliations = author_data.get("affiliations") or []

    # Group affiliations by institution type
    education_affs = []
    company_affs = []

    for aff in affiliations:
        inst = aff.get("institution")
        if not inst:
            continue

        inst_type = inst.get("type")
        if inst_type == "education":
            education_affs.append(aff)
        elif inst_type == "company":
            company_affs.append(aff)

    # Select the education institution with most publication years
    if education_affs:
        education_affs.sort(key=lambda x: len(x.get("years", [])), reverse=True)
        edu = education_affs[0]["institution"]
        result["primary_education"] = {
            "id": extract_short_id(edu.get("id", "")),
            "name": edu.get("display_name"),
        }

    # Select the company institution with most publication years
    if company_affs:
        company_affs.sort(key=lambda x: len(x.get("years", [])), reverse=True)
        comp = company_affs[0]["institution"]
        result["primary_company"] = {
            "id": extract_short_id(comp.get("id", "")),
            "name": comp.get("display_name"),
        }

    return result


class AuthorFetcher:
    """Fetcher for authors from OpenAlex"""

    def __init__(self, session: AsyncSession, client: OpenAlexClient | None = None):
        self.session = session
        self.client = client or OpenAlexClient()
        self.repo = RawAuthorRepository(session)

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

    async def fetch_authors_by_ids(
        self,
        author_ids: list[str],
        task_id: int | None = None,
        progress_callback: callable | None = None,
        refresh_days: int = 30,
    ) -> FetchProgress:
        """Fetch authors by their OpenAlex IDs

        Also refreshes existing authors whose data is older than refresh_days.
        """
        progress = FetchProgress()
        progress.total = len(author_ids)
        progress.current_step = "Fetching authors from OpenAlex"

        logger.info(f"开始获取作者数据: 共 {len(author_ids)} 位作者")

        # Find which authors are already in database
        missing_ids = await self.repo.get_missing_author_ids(author_ids)

        # Find stale authors (existing but fetched too long ago)
        stale_ids: list[str] = []
        if refresh_days > 0:
            existing_authors = await self.repo.get_by_openalex_ids(author_ids)
            stale_threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
                days=refresh_days
            )
            for author in existing_authors:
                if author.fetched_at is None or author.fetched_at < stale_threshold:
                    stale_ids.append(author.openalex_author_id)

        # Merge missing and stale, preserving order (missing first)
        stale_ids = [aid for aid in stale_ids if aid not in missing_ids]
        ids_to_fetch = missing_ids + stale_ids

        progress.current_step = (
            f"Fetching {len(ids_to_fetch)} authors ({len(missing_ids)} new, {len(stale_ids)} stale)"
        )

        logger.info(
            f"其中 {len(missing_ids)} 位新增需要从 API 获取，"
            f"{len(stale_ids)} 位数据过期需要刷新，"
            f"{len(author_ids) - len(ids_to_fetch)} 位已存在且最新"
        )

        # Determine proxy for OpenAlex API
        openalex_url = f"{OPENALEX_API_BASE}/authors"
        proxy = self.client.get_proxy_for_request(openalex_url)
        async with self.client.create_session() as http_session:
            batch_size = min(settings.EMBEDDING_BATCH_SIZE, 50)
            total_batches = (len(ids_to_fetch) + batch_size - 1) // batch_size

            for i in range(0, len(ids_to_fetch), batch_size):
                batch = ids_to_fetch[i : i + batch_size]
                batch_num = i // batch_size + 1

                try:
                    url = f"{OPENALEX_API_BASE}/authors"
                    params = {"filter": f"openalex:{'|'.join(batch)}", "per_page": 50}

                    headers = {}
                    if self.client.email:
                        headers["mailto"] = self.client.email

                    data = await self._fetch_batch_with_retry(
                        http_session, url, params, headers, proxy
                    )

                    authors = data.get("results", [])
                    batch_authors: list[RawAuthor] = []
                    for author_data in authors:
                        try:
                            # OpenAlex returns 'last_known_institutions' (plural, list)
                            # Take the first institution if available (legacy field)
                            inst_list = author_data.get("last_known_institutions") or []
                            inst_info = inst_list[0] if inst_list else {}

                            # Extract primary institutions by publication count
                            institutions = extract_institutions(author_data)
                            primary_edu = institutions.get("primary_education") or {}
                            primary_comp = institutions.get("primary_company") or {}

                            raw_author = RawAuthor(
                                openalex_author_id=extract_short_id(author_data.get("id", "")),
                                raw_json=json.dumps(author_data),
                                display_name=author_data.get("display_name"),
                                orcid=author_data.get("orcid"),
                                works_count=author_data.get("works_count", 0),
                                cited_by_count=author_data.get("cited_by_count", 0),
                                h_index=author_data.get("summary_stats", {}).get("h_index", 0),
                                i10_index=author_data.get("summary_stats", {}).get("i10_index", 0),
                                # Legacy fields
                                last_known_institution_id=extract_short_id(inst_info.get("id", "")),
                                last_known_institution_name=inst_info.get("display_name"),
                                # Primary institutions (by publication count)
                                primary_education_id=primary_edu.get("id"),
                                primary_education_name=primary_edu.get("name"),
                                primary_company_id=primary_comp.get("id"),
                                primary_company_name=primary_comp.get("name"),
                                fetch_task_id=task_id,
                                fetched_at=datetime.now(timezone.utc).replace(tzinfo=None),
                            )
                            batch_authors.append(raw_author)
                            progress.fetched += 1
                        except Exception as e:
                            logger.warning(f"解析作者数据失败: {e}")
                            progress.failed += 1

                    if batch_authors:
                        await self.repo.batch_upsert(batch_authors)
                        batch_authors = []

                    # 每 10 批提交一次（约 500 条），减少锁持有时间
                    if batch_num % 10 == 0:
                        await self.session.commit()
                        logger.info(
                            f"作者获取进度: {batch_num}/{total_batches} 批次, 已获取 {progress.fetched} 位"
                        )

                except Exception as e:
                    logger.error(f"批次 {batch_num} 获取失败: {e}")
                    progress.failed += len(batch)

                if progress_callback:
                    progress_callback(progress)

                await asyncio.sleep(REQUEST_DELAY)

        logger.info(f"作者获取完成: 共 {progress.fetched} 位, 失败 {progress.failed} 位")
        return progress
