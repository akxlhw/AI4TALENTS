"""
OpenAlex data fetchers for the raw data layer.
OpenAlex 数据采集器 - 负责从 API 获取数据并存入原始数据层
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.domains.academic.models.raw_data import RawAuthor, RawInstitution, RawWork
from app.domains.academic.models.venue import Venue
from app.domains.academic.repositories.raw_data_repository import (
    RawAuthorRepository,
    RawInstitutionRepository,
    RawWorkRepository,
)
from app.domains.academic.services.common.openalex_utils import (
    OPENALEX_API_BASE,
    REQUEST_DELAY,
    extract_short_id,
)
from app.domains.academic.services.common.progress import FetchProgress
from app.domains.shared.services.common.circuit_breaker import CircuitBreaker

# Circuit breaker for OpenAlex data fetchers (shared across WorkFetcher/AuthorFetcher/InstitutionFetcher)
_openalex_fetcher_breaker = CircuitBreaker(
    name="openalex_data_fetcher",
    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    window_size=settings.CIRCUIT_BREAKER_WINDOW_SIZE,
)

logger = logging.getLogger(__name__)

# Maximum records to fetch per venue (0 = no limit)
# Can be overridden via environment variable
MAX_WORKS_PER_VENUE = int(os.environ.get("MAX_WORKS_PER_VENUE", "0"))  # 0 means no limit

# API 请求超时配置
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(
    total=120, connect=30, sock_read=60  # 总超时 120 秒  # 连接超时 30 秒  # 读取超时 60 秒
)


class RetryableError(Exception):
    """可重试的错误（如速率限制、临时网络问题）"""

    pass


def with_retry(max_attempts: int = 3, min_wait: float = 1.0, max_wait: float = 60.0):
    """创建重试装饰器

    Args:
        max_attempts: 最大重试次数
        min_wait: 最小等待时间（秒）
        max_wait: 最大等待时间（秒）

    Returns:
        重试装饰器
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(RetryableError),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


class OpenAlexClient:
    """OpenAlex API client configuration for fetchers.

    Note: This is a lightweight config holder. Actual HTTP requests are made
    directly by the Fetcher classes using aiohttp for better async control.
    Proxy configuration is managed by HttpClientFactory.
    """

    def __init__(self, email: str | None = None):
        self.email = email
        self.base_url = OPENALEX_API_BASE

    def create_session(self, timeout=None):
        """Create aiohttp session aligned with HttpClientFactory config."""
        from app.domains.shared.services.common.http_client import HttpClientFactory

        connector = aiohttp.TCPConnector(ssl=HttpClientFactory.get_ssl_verify())
        kwargs = {"trust_env": False, "connector": connector}
        if timeout:
            kwargs["timeout"] = timeout
        return aiohttp.ClientSession(**kwargs)

    def get_proxy_for_request(self, url: str) -> str | None:
        """
        Get proxy URL for a specific request using HttpClientFactory.

        Args:
            url: Target URL

        Returns:
            Proxy URL string or None for direct connection
        """
        from app.domains.shared.services.common.http_client import HttpClientFactory

        return HttpClientFactory.get_proxy_for_url(url)


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
            async with http_session.get(
                url, params=params, headers=headers, proxy=proxy
            ) as response:
                if response.status == 429:
                    # 速率限制，触发重试
                    raise RetryableError("Rate limited (HTTP 429)")
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
                async with http_session.get(
                    url, params=params, headers=headers, proxy=proxy
                ) as response:
                    if response.status == 429:
                        raise RetryableError("Rate limited (HTTP 429)")
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
            async with http_session.get(
                url, params=params, headers=headers, proxy=proxy
            ) as response:
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
            async with http_session.get(
                url, params=params, headers=headers, proxy=proxy
            ) as response:
                if response.status == 429:
                    raise RetryableError("Rate limited (HTTP 429)")
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
            async with http_session.get(
                url, params=params, headers=headers, proxy=proxy
            ) as response:
                if response.status == 429:
                    raise RetryableError("Rate limited (HTTP 429)")
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
