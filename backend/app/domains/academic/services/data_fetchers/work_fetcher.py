"""Work fetcher for the OpenAlex raw data layer.

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
from app.domains.academic.models.raw_data import RawWork
from app.domains.academic.models.venue import Venue
from app.domains.academic.repositories.raw_data_repository import RawWorkRepository
from app.domains.academic.services.common.openalex_utils import (
    OPENALEX_API_BASE,
    REQUEST_DELAY,
    extract_short_id,
)
from app.domains.academic.services.common.progress import FetchProgress
from app.domains.academic.services.data_fetchers.common import (
    DEFAULT_TIMEOUT,
    MAX_WORKS_PER_VENUE,
    OpenAlexClient,
    RetryableError,
    _openalex_fetcher_breaker,
    _rate_limited_error,
    _record_upstream,
    with_retry,
)

logger = logging.getLogger(__name__)


class WorkFetcher:
    """Fetcher for works from OpenAlex"""

    def __init__(self, session: AsyncSession, client: OpenAlexClient | None = None):
        self.session = session
        self.client = client or OpenAlexClient()
        self.repo = RawWorkRepository(session)

    @with_retry(max_attempts=5, max_wait=60.0)
    async def _fetch_page_with_retry(
        self,
        http_session: aiohttp.ClientSession,
        url: str,
        params: dict,
        headers: dict,
        proxy: str | None = None,
    ) -> dict:
        """带重试和熔断保护的单页获取

        Args:
            http_session: aiohttp 会话
            url: 请求 URL
            params: 请求参数
            headers: 请求头
            proxy: 代理服务器 URL

        Returns:
            JSON 响应数据

        Raises:
            RetryableError: 可重试的错误（速率限制、服务器错误、临时网络问题）
            CircuitBreakerOpenError: 熔断器打开时直接拒绝请求
        """

        async def _do_fetch() -> dict:
            started = time.monotonic()
            async with http_session.get(
                url, params=params, headers=headers, proxy=proxy
            ) as response:
                _record_upstream(response.status, started)
                if response.status == 429:
                    # 速率限制，触发重试（尊重 Retry-After 头）
                    raise _rate_limited_error(response)
                if response.status >= 500:
                    # 服务器错误（5xx）也触发重试，提升企业内网稳定性
                    raise RetryableError(f"Server error (HTTP {response.status})")
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                return await response.json()

        if not settings.CIRCUIT_BREAKER_ENABLED:
            return await _do_fetch()
        return await _openalex_fetcher_breaker.call(_do_fetch)

    @with_retry(max_attempts=3, max_wait=30.0)
    async def _fetch_work_count(
        self,
        url: str,
        params: dict,
        headers: dict,
        proxy: str | None,
    ) -> int:
        """Fetch work count with retry and circuit breaker support."""

        async def _do_fetch() -> int:
            async with self.client.create_session(timeout=DEFAULT_TIMEOUT) as http_session:
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
                    data = await response.json()
                    return data.get("meta", {}).get("count", 0)

        if not settings.CIRCUIT_BREAKER_ENABLED:
            return await _do_fetch()
        return await _openalex_fetcher_breaker.call(_do_fetch)

    async def get_work_count_from_venue(
        self, venue: Venue, year_from: int | None = None, year_to: int | None = None
    ) -> int:
        """获取 Venue 的预计论文总数（不获取实际数据）

        Uses OpenAlex API's meta.count field to get total count without fetching data.
        Supports date filtering for accurate incremental collection estimates.

        Args:
            venue: Venue 对象，包含 openalex_source_id
            year_from: 起始年份
            year_to: 结束年份

        Returns:
            预计论文总数，如果请求失败返回 0
        """
        if not venue.openalex_source_id:
            return 0

        url = f"{OPENALEX_API_BASE}/works"
        # Use locations.source.id to include papers where venue is not primary_location
        # (e.g., conference papers first published on arXiv)
        filters = [f"locations.source.id:{venue.openalex_source_id}"]

        # Add date filters if provided
        if year_from:
            filters.append(f"from_publication_date:{year_from}-01-01")
        if year_to:
            filters.append(f"to_publication_date:{year_to}-12-31")

        params = {
            "filter": ",".join(filters),
            "per_page": 1,  # 只请求 1 条以减少响应体
            "cursor": "*",
        }

        headers = {}
        if self.client.email:
            headers["mailto"] = self.client.email

        # Determine proxy for OpenAlex API requests
        openalex_url = f"{OPENALEX_API_BASE}/works"
        proxy = self.client.get_proxy_for_request(openalex_url)

        try:
            return await self._fetch_work_count(url, params, headers, proxy)
        except Exception as e:
            logger.warning(f"Failed to get work count for venue {venue.venue_name}: {e}")
            return 0

    async def fetch_works_from_venue(
        self,
        venue: Venue,
        year_from: int | None = None,
        year_to: int | None = None,
        task_id: int | None = None,
        sub_task_id: int | None = None,
        progress_callback: callable | None = None,
    ) -> FetchProgress:
        """Fetch all works from a venue with retry support"""
        progress = FetchProgress()
        progress.current_step = f"Fetching works from {venue.venue_name}"

        if not venue.openalex_source_id:
            progress.current_step = f"Venue {venue.venue_name} has no OpenAlex source ID"
            return progress

        # Determine proxy for OpenAlex API requests
        openalex_url = f"{OPENALEX_API_BASE}/works"
        proxy = self.client.get_proxy_for_request(openalex_url)

        async with self.client.create_session(timeout=DEFAULT_TIMEOUT) as http_session:
            cursor = "*"
            total_fetched = 0
            batch_size = settings.SYNC_COMMIT_BATCH_SIZE
            batch_works: list[RawWork] = []

            while cursor:
                # Check if we've reached the max limit (0 = no limit)
                if MAX_WORKS_PER_VENUE > 0 and total_fetched >= MAX_WORKS_PER_VENUE:
                    progress.current_step = f"Reached max limit ({MAX_WORKS_PER_VENUE} records)"
                    break

                url = f"{OPENALEX_API_BASE}/works"

                # Build filters: source + optional date range
                # Note: Use locations.source.id instead of primary_location.source.id
                # because many conference papers (e.g., NeurIPS, ICML) have arXiv as primary_location
                # while the conference is only in locations array
                filters = [f"locations.source.id:{venue.openalex_source_id}"]
                if year_from:
                    filters.append(f"from_publication_date:{year_from}-01-01")
                if year_to:
                    filters.append(f"to_publication_date:{year_to}-12-31")

                params = {"filter": ",".join(filters), "per_page": 200, "cursor": cursor}

                headers = {}
                if self.client.email:
                    headers["mailto"] = self.client.email

                # 使用带重试的请求方法
                try:
                    data = await self._fetch_page_with_retry(
                        http_session, url, params, headers, proxy
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch page after retries for venue {venue.venue_name}: {e}. "
                        f"Cursor={cursor}, already_fetched={total_fetched}. "
                        f"Remaining pages will be skipped."
                    )
                    progress.failed += 1
                    break

                works = data.get("results", [])
                progress.total = data.get("meta", {}).get("count", 0)

                for work_data in works:
                    try:
                        author_ids = []
                        authorships = work_data.get("authorships", [])
                        for authorship in authorships:
                            author_id = extract_short_id(authorship.get("author", {}).get("id", ""))
                            if author_id:
                                author_ids.append(author_id)

                        raw_work = RawWork(
                            openalex_work_id=extract_short_id(work_data.get("id", "")),
                            raw_json=json.dumps(work_data),
                            title=work_data.get("title"),
                            doi=work_data.get("doi"),
                            publication_year=work_data.get("publication_year"),
                            publication_date=work_data.get("publication_date"),
                            source_id=venue.openalex_source_id,
                            source_name=venue.venue_name,
                            author_count=len(author_ids),
                            author_ids=json.dumps(author_ids),
                            fetch_task_id=task_id,
                            sub_task_id=sub_task_id,
                            fetched_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        )
                        batch_works.append(raw_work)
                        total_fetched += 1
                        progress.fetched = total_fetched

                        # Batch upsert and commit every batch_size records
                        if total_fetched % batch_size == 0:
                            if batch_works:
                                await self.repo.batch_upsert(batch_works)
                                batch_works = []
                            await self.session.commit()
                    except Exception as e:
                        # Log the error and continue with next work
                        logger.warning(f"Failed to insert work: {e}")
                        progress.failed += 1
                        # Continue with next work instead of breaking

                if progress_callback:
                    progress_callback(progress)

                # Get next cursor
                cursor = data.get("meta", {}).get("next_cursor")
                if cursor:
                    await asyncio.sleep(REQUEST_DELAY)

            # Flush remaining works in the last batch
            if batch_works:
                await self.repo.batch_upsert(batch_works)
                await self.session.commit()

        return progress

    async def fetch_author_top_works(
        self, openalex_author_id: str, max_works: int = 10
    ) -> list[dict]:
        """获取作者的代表作品（按引用数排序）

        Args:
            openalex_author_id: OpenAlex 作者 ID（短格式，如 "A123456789"）
            max_works: 最大返回数量，默认 10 篇

        Returns:
            List[dict]: 代表作品列表，每项包含 title, publication_year, citation_count, venue_name, doi, source_work_id
        """
        url = f"{OPENALEX_API_BASE}/works"
        params = {
            "filter": f"author.id:{openalex_author_id}",
            "sort": "cited_by_count:desc",
            "per_page": max_works,
        }

        headers = {}
        if self.client.email:
            headers["mailto"] = self.client.email

        works = []
        proxy = self.client.get_proxy_for_request(url)
        async with self.client.create_session() as http_session:
            started = time.monotonic()
            async with http_session.get(
                url, params=params, headers=headers, proxy=proxy
            ) as response:
                _record_upstream(response.status, started)
                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch works for author {openalex_author_id}: HTTP {response.status}"
                    )
                    return works

                data = await response.json()
                results = data.get("results", [])

                for work_data in results:
                    try:
                        # 提取期刊/会议名称
                        primary_location = work_data.get("primary_location") or {}
                        source = primary_location.get("source") or {}
                        venue_name = source.get("display_name")

                        work_info = {
                            "title": work_data.get("title"),
                            "publication_year": work_data.get("publication_year"),
                            "citation_count": work_data.get("cited_by_count", 0),
                            "venue_name": venue_name,
                            "doi": work_data.get("doi"),
                            "source_work_id": extract_short_id(work_data.get("id", "")),
                        }
                        works.append(work_info)
                    except Exception as e:
                        logger.warning(f"Error parsing work data: {e}")
                        continue

        return works

    async def compute_selected_works_for_all_authors(
        self, task_id: int | None = None, max_works: int = 10
    ) -> dict[str, list[dict]]:
        """从本地 RawWork 一次性计算所有学者的代表作（按引用数排序）

        直接从已采集的 RawWork 中解析论文数据，避免重复调用外部 API，
        提升企业内网环境下的稳定性和性能。

        Args:
            task_id: 采集任务 ID。为 None 时处理所有论文，否则只处理该任务。
            max_works: 每位学者最多返回的代表作数量。

        Returns:
            dict: {openalex_author_id: [work_info, ...]}，已按引用数降序排列。
                  work_info 包含 title, publication_year, citation_count,
                  venue_name, doi, source_work_id。
        """
        from collections import defaultdict

        from sqlalchemy import select

        query = select(RawWork)
        if task_id is not None:
            query = query.where(RawWork.fetch_task_id == task_id)

        result = await self.session.execute(query)
        works = result.scalars().all()

        author_works_map: dict[str, list[dict]] = defaultdict(list)
        # 用 (author_id, openalex_work_id) 组合去重，
        # 避免同一篇论文在不同 venue 中被重复采集导致重复
        seen_pairs: set[str] = set()

        for work in works:
            if not work.author_ids or not work.raw_json:
                continue

            try:
                author_ids = json.loads(work.author_ids)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(author_ids, list) or not author_ids:
                continue

            try:
                data = json.loads(work.raw_json)
            except (json.JSONDecodeError, TypeError):
                continue

            # 过滤无标题论文
            title = (data.get("title") or work.title or "").strip()
            if not title:
                continue

            # 提取期刊/会议名称
            primary_location = data.get("primary_location") or {}
            source = primary_location.get("source") or {}
            venue_name = source.get("display_name")

            work_info = {
                "title": title,
                "publication_year": data.get("publication_year") or work.publication_year,
                "citation_count": data.get("cited_by_count", 0) or 0,
                "venue_name": venue_name,
                "doi": data.get("doi") or work.doi,
                "source_work_id": work.openalex_work_id,
            }

            for author_id in author_ids:
                if not author_id:
                    continue
                pair_key = f"{author_id}:{work.openalex_work_id}"
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                author_works_map[author_id].append(work_info)

        # 按引用数降序排序并截断
        final_map: dict[str, list[dict]] = {}
        for author_id, work_list in author_works_map.items():
            work_list.sort(key=lambda x: x["citation_count"], reverse=True)
            final_map[author_id] = work_list[:max_works]

        return final_map
