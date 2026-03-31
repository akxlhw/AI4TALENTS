"""
OpenAlex data fetchers for the raw data layer.
OpenAlex 数据采集器 - 负责从 API 获取数据并存入原始数据层
"""
import json
import asyncio
import aiohttp
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.models.raw_data import RawWork, RawAuthor, RawInstitution
from app.models.venue import Venue
from app.repositories.raw_data_repository import (
    RawWorkRepository, RawAuthorRepository, RawInstitutionRepository
)
from app.services.common.openalex_utils import (
    extract_short_id, OPENALEX_API_BASE, REQUEST_DELAY
)
from app.services.common.progress import FetchProgress

logger = logging.getLogger(__name__)

# Maximum records to fetch per venue (0 = no limit)
# Can be overridden via environment variable or task config
MAX_WORKS_PER_VENUE = 0  # 0 means no limit

# API 请求超时配置
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(
    total=30,      # 总超时 30 秒
    connect=10,    # 连接超时 10 秒
    sock_read=30   # 读取超时 30 秒
)


class RetryableError(Exception):
    """可重试的错误（如速率限制、临时网络问题）"""
    pass


def with_retry(max_attempts: int = 3, min_wait: float = 1.0, max_wait: float = 10.0):
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
        reraise=True
    )


class OpenAlexClient:
    """OpenAlex API client configuration for fetchers.

    Note: This is a lightweight config holder. Actual HTTP requests are made
    directly by the Fetcher classes using aiohttp for better async control.
    """

    def __init__(self, email: Optional[str] = None):
        self.email = email
        self.base_url = OPENALEX_API_BASE


class WorkFetcher:
    """Fetcher for works from OpenAlex"""

    def __init__(self, session: AsyncSession, client: Optional[OpenAlexClient] = None):
        self.session = session
        self.client = client or OpenAlexClient()
        self.repo = RawWorkRepository(session)

    @with_retry(max_attempts=3)
    async def _fetch_page_with_retry(
        self,
        http_session: aiohttp.ClientSession,
        url: str,
        params: dict,
        headers: dict
    ) -> dict:
        """带重试的单页获取

        Args:
            http_session: aiohttp 会话
            url: 请求 URL
            params: 请求参数
            headers: 请求头

        Returns:
            JSON 响应数据

        Raises:
            RetryableError: 可重试的错误（速率限制、临时网络问题）
        """
        async with http_session.get(url, params=params, headers=headers) as response:
            if response.status == 429:
                # 速率限制，触发重试
                raise RetryableError(f"Rate limited (HTTP 429)")
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            return await response.json()

    async def get_work_count_from_venue(
        self,
        venue: Venue,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
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
        filters = [f"primary_location.source.id:{venue.openalex_source_id}"]

        # Add date filters if provided
        if year_from:
            filters.append(f"from_publication_date:{year_from}-01-01")
        if year_to:
            filters.append(f"to_publication_date:{year_to}-12-31")

        params = {
            "filter": ",".join(filters),
            "per_page": 1,      # 只请求 1 条以减少响应体
            "cursor": "*"
        }

        headers = {}
        if self.client.email:
            headers["mailto"] = self.client.email

        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    return 0
                data = await response.json()
                return data.get("meta", {}).get("count", 0)

    async def fetch_works_from_venue(
        self,
        venue: Venue,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        task_id: Optional[int] = None,
        sub_task_id: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> FetchProgress:
        """Fetch all works from a venue with retry support"""
        progress = FetchProgress()
        progress.current_step = f"Fetching works from {venue.venue_name}"

        if not venue.openalex_source_id:
            progress.current_step = f"Venue {venue.venue_name} has no OpenAlex source ID"
            return progress

        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as http_session:
            cursor = "*"
            total_fetched = 0
            batch_size = 100  # Commit every 100 records

            while cursor:
                # Check if we've reached the max limit (0 = no limit)
                if MAX_WORKS_PER_VENUE > 0 and total_fetched >= MAX_WORKS_PER_VENUE:
                    progress.current_step = f"Reached max limit ({MAX_WORKS_PER_VENUE} records)"
                    break

                url = f"{OPENALEX_API_BASE}/works"

                # Build filters: source + optional date range
                # Note: OpenAlex API DOES support combining source and date filters
                filters = [f"primary_location.source.id:{venue.openalex_source_id}"]
                if year_from:
                    filters.append(f"from_publication_date:{year_from}-01-01")
                if year_to:
                    filters.append(f"to_publication_date:{year_to}-12-31")

                params = {
                    "filter": ",".join(filters),
                    "per_page": 200,
                    "cursor": cursor
                }

                headers = {}
                if self.client.email:
                    headers["mailto"] = self.client.email

                # 使用带重试的请求方法
                try:
                    data = await self._fetch_page_with_retry(http_session, url, params, headers)
                except Exception as e:
                    logger.warning(f"Failed to fetch page after retries: {e}")
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
                            fetched_at=datetime.now(timezone.utc)
                        )
                        await self.repo.upsert(raw_work)
                        total_fetched += 1
                        progress.fetched = total_fetched

                        # Commit every batch_size records to avoid losing data on timeout
                        if total_fetched % batch_size == 0:
                            await self.session.commit()
                    except Exception as e:
                        progress.failed += 1

                if progress_callback:
                    progress_callback(progress)

                # Get next cursor
                cursor = data.get("meta", {}).get("next_cursor")
                if cursor:
                    await asyncio.sleep(REQUEST_DELAY)

        return progress

    async def fetch_author_top_works(
        self,
        openalex_author_id: str,
        max_works: int = 10
    ) -> List[dict]:
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
            "per_page": max_works
        }

        headers = {}
        if self.client.email:
            headers["mailto"] = self.client.email

        works = []
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch works for author {openalex_author_id}: HTTP {response.status}")
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
                            "source_work_id": extract_short_id(work_data.get("id", ""))
                        }
                        works.append(work_info)
                    except Exception as e:
                        logger.warning(f"Error parsing work data: {e}")
                        continue

        return works


class AuthorFetcher:
    """Fetcher for authors from OpenAlex"""

    def __init__(self, session: AsyncSession, client: Optional[OpenAlexClient] = None):
        self.session = session
        self.client = client or OpenAlexClient()
        self.repo = RawAuthorRepository(session)

    async def fetch_authors_by_ids(
        self,
        author_ids: List[str],
        task_id: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> FetchProgress:
        """Fetch authors by their OpenAlex IDs"""
        progress = FetchProgress()
        progress.total = len(author_ids)
        progress.current_step = "Fetching authors from OpenAlex"

        logger.info(f"开始获取作者数据: 共 {len(author_ids)} 位作者")

        # Find which authors are already in database
        missing_ids = await self.repo.get_missing_author_ids(author_ids)
        progress.current_step = f"Fetching {len(missing_ids)} new authors"

        logger.info(f"其中 {len(missing_ids)} 位需要从 API 获取，{len(author_ids) - len(missing_ids)} 位已存在")

        async with aiohttp.ClientSession() as http_session:
            batch_size = 50
            total_batches = (len(missing_ids) + batch_size - 1) // batch_size

            for i in range(0, len(missing_ids), batch_size):
                batch = missing_ids[i:i + batch_size]
                batch_num = i // batch_size + 1

                try:
                    url = f"{OPENALEX_API_BASE}/authors"
                    params = {
                        "filter": f"openalex:{'|'.join(batch)}",
                        "per_page": 50
                    }

                    headers = {}
                    if self.client.email:
                        headers["mailto"] = self.client.email

                    async with http_session.get(url, params=params, headers=headers) as response:
                        if response.status != 200:
                            logger.warning(f"批次 {batch_num}/{total_batches} 请求失败: HTTP {response.status}")
                            progress.failed += len(batch)
                            continue

                        data = await response.json()

                    authors = data.get("results", [])
                    batch_fetched = 0
                    for author_data in authors:
                        try:
                            # OpenAlex returns 'last_known_institutions' (plural, list)
                            # Take the first institution if available
                            inst_list = author_data.get("last_known_institutions") or []
                            inst_info = inst_list[0] if inst_list else {}

                            raw_author = RawAuthor(
                                openalex_author_id=extract_short_id(author_data.get("id", "")),
                                raw_json=json.dumps(author_data),
                                display_name=author_data.get("display_name"),
                                orcid=author_data.get("orcid"),
                                works_count=author_data.get("works_count", 0),
                                cited_by_count=author_data.get("cited_by_count", 0),
                                h_index=author_data.get("summary_stats", {}).get("h_index", 0),
                                i10_index=author_data.get("summary_stats", {}).get("i10_index", 0),
                                last_known_institution_id=extract_short_id(inst_info.get("id", "")),
                                last_known_institution_name=inst_info.get("display_name"),
                                fetch_task_id=task_id,
                                fetched_at=datetime.now(timezone.utc)
                            )
                            await self.repo.upsert(raw_author)
                            progress.fetched += 1
                            batch_fetched += 1
                        except Exception as e:
                            logger.warning(f"解析作者数据失败: {e}")
                            progress.failed += 1

                    # 每 10 批提交一次（约 500 条），减少锁持有时间
                    if batch_num % 10 == 0:
                        await self.session.commit()
                        logger.info(f"作者获取进度: {batch_num}/{total_batches} 批次, 已获取 {progress.fetched} 位")

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

    def __init__(self, session: AsyncSession, client: Optional[OpenAlexClient] = None):
        self.session = session
        self.client = client or OpenAlexClient()
        self.repo = RawInstitutionRepository(session)

    async def fetch_institutions_by_ids(
        self,
        institution_ids: List[str],
        task_id: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> FetchProgress:
        """Fetch institutions by their OpenAlex IDs"""
        progress = FetchProgress()
        progress.total = len(institution_ids)
        progress.current_step = "Fetching institutions from OpenAlex"

        logger.info(f"开始获取机构数据: 共 {len(institution_ids)} 个机构")

        # Find which institutions are already in database
        missing_ids = await self.repo.get_missing_ids(institution_ids)
        progress.current_step = f"Fetching {len(missing_ids)} new institutions"

        logger.info(f"其中 {len(missing_ids)} 个需要从 API 获取，{len(institution_ids) - len(missing_ids)} 个已存在")

        async with aiohttp.ClientSession() as http_session:
            batch_size = 50
            total_batches = (len(missing_ids) + batch_size - 1) // batch_size

            for i in range(0, len(missing_ids), batch_size):
                batch = missing_ids[i:i + batch_size]
                batch_num = i // batch_size + 1

                try:
                    url = f"{OPENALEX_API_BASE}/institutions"
                    params = {
                        "filter": f"openalex:{'|'.join(batch)}",
                        "per_page": 50
                    }

                    headers = {}
                    if self.client.email:
                        headers["mailto"] = self.client.email

                    async with http_session.get(url, params=params, headers=headers) as response:
                        if response.status != 200:
                            logger.warning(f"批次 {batch_num}/{total_batches} 请求失败: HTTP {response.status}")
                            progress.failed += len(batch)
                            continue

                        data = await response.json()

                    institutions = data.get("results", [])
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
                                fetched_at=datetime.now(timezone.utc)
                            )
                            await self.repo.upsert(raw_inst)
                            progress.fetched += 1
                        except Exception as e:
                            logger.warning(f"解析机构数据失败: {e}")
                            progress.failed += 1

                    # 每 5 批提交一次，减少锁持有时间
                    if batch_num % 5 == 0:
                        await self.session.commit()
                        logger.info(f"机构获取进度: {batch_num}/{total_batches} 批次, 已获取 {progress.fetched} 个")

                except Exception as e:
                    logger.error(f"批次 {batch_num} 获取失败: {e}")
                    progress.failed += len(batch)

                if progress_callback:
                    progress_callback(progress)

                await asyncio.sleep(REQUEST_DELAY)

        logger.info(f"机构获取完成: 共 {progress.fetched} 个, 失败 {progress.failed} 个")
        return progress
