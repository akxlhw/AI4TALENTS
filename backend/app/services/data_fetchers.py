"""
OpenAlex data fetchers for the raw data layer.
OpenAlex 数据采集器 - 负责从 API 获取数据并存入原始数据层
"""
import json
import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

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
        """Fetch all works from a venue"""
        progress = FetchProgress()
        progress.current_step = f"Fetching works from {venue.venue_name}"

        if not venue.openalex_source_id:
            progress.current_step = f"Venue {venue.venue_name} has no OpenAlex source ID"
            return progress

        async with aiohttp.ClientSession() as http_session:
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

                async with http_session.get(url, params=params, headers=headers) as response:
                    if response.status != 200:
                        progress.failed += 1
                        break

                    data = await response.json()

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
                            fetched_at=datetime.utcnow()
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

        # Find which authors are already in database
        missing_ids = await self.repo.get_missing_author_ids(author_ids)
        progress.current_step = f"Fetching {len(missing_ids)} new authors"

        async with aiohttp.ClientSession() as http_session:
            batch_size = 50
            for i in range(0, len(missing_ids), batch_size):
                batch = missing_ids[i:i + batch_size]

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
                            progress.failed += len(batch)
                            continue

                        data = await response.json()

                    authors = data.get("results", [])
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
                                fetched_at=datetime.utcnow()
                            )
                            await self.repo.upsert(raw_author)
                            progress.fetched += 1
                        except Exception as e:
                            progress.failed += 1

                except Exception as e:
                    progress.failed += len(batch)

                if progress_callback:
                    progress_callback(progress)

                await asyncio.sleep(REQUEST_DELAY)

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

        # Find which institutions are already in database
        missing_ids = await self.repo.get_missing_ids(institution_ids)
        progress.current_step = f"Fetching {len(missing_ids)} new institutions"

        async with aiohttp.ClientSession() as http_session:
            batch_size = 50
            for i in range(0, len(missing_ids), batch_size):
                batch = missing_ids[i:i + batch_size]

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
                                fetched_at=datetime.utcnow()
                            )
                            await self.repo.upsert(raw_inst)
                            progress.fetched += 1
                        except Exception as e:
                            progress.failed += 1

                except Exception as e:
                    progress.failed += len(batch)

                if progress_callback:
                    progress_callback(progress)

                await asyncio.sleep(REQUEST_DELAY)

        return progress
