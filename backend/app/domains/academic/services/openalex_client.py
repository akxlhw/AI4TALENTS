"""
OpenAlex API Client.
Handles communication with the OpenAlex API.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.domains.shared.services.common.http_client import HttpClientFactory


class OpenAlexAPIError(Exception):
    """Custom exception for OpenAlex API errors."""

    pass


class OpenAlexRateLimitError(OpenAlexAPIError):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class OpenAlexClient:
    """
    Client for interacting with OpenAlex API.

    Documentation: https://docs.openalex.org/
    """

    BASE_URL = "https://api.openalex.org"

    # Endpoints
    WORKS = "/works"
    AUTHORS = "/authors"
    INSTITUTIONS = "/institutions"
    CONCEPTS = "/concepts"

    def __init__(
        self,
        email: str | None = None,
        rate_limit: int = 10,
        timeout: int = 30,
    ):
        """
        Initialize OpenAlex client.

        Args:
            email: Email for polite API access (higher rate limits)
            rate_limit: Maximum requests per second
            timeout: Request timeout in seconds
        """
        self.email = email or settings.OPENALEX_EMAIL
        self.rate_limit = rate_limit or settings.OPENALEX_RATE_LIMIT
        self.timeout = timeout
        self.base_url = settings.OPENALEX_BASE_URL or self.BASE_URL

        # Rate limiting
        self._last_request_time = 0.0
        self._min_interval = 1.0 / self.rate_limit

        # Headers
        self.headers = {
            "Accept": "application/json",
            "User-Agent": (
                f"TalentPlatform/1.0 (mailto:{self.email})" if self.email else "TalentPlatform/1.0"
            ),
        }

        # Reusable HTTP client via factory (proxy + no_proxy support)
        self._client = HttpClientFactory.create_client_for_url(
            self.base_url,
            timeout=self.timeout,
            headers=self.headers,
        )

    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    async def _async_wait_for_rate_limit(self):
        """Async version of rate limit wait."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    @staticmethod
    def _retry_wait(retry_state: RetryCallState) -> float:
        """Custom wait: prefer API's Retry-After header, fallback to exponential backoff."""
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if isinstance(exc, OpenAlexRateLimitError) and exc.retry_after:
            return float(exc.retry_after)
        return wait_exponential(multiplier=1, min=1, max=10)(retry_state)

    @retry(
        stop=stop_after_attempt(5),
        wait=_retry_wait,
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, OpenAlexRateLimitError)
        ),
        reraise=True,
    )
    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make a rate-limited request to OpenAlex API.

        Args:
            client: HTTP client instance
            endpoint: API endpoint (e.g., /authors)
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            OpenAlexAPIError: On API errors
            OpenAlexRateLimitError: On rate limit exceeded
        """
        await self._async_wait_for_rate_limit()

        url = f"{self.base_url}{endpoint}"

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = None
                raw = e.response.headers.get("Retry-After")
                if raw:
                    try:
                        retry_after = int(raw)
                    except (ValueError, TypeError):
                        pass
                raise OpenAlexRateLimitError(
                    f"Rate limit exceeded (retry_after={retry_after})",
                    retry_after=retry_after,
                ) from e
            raise OpenAlexAPIError(
                f"API error: {e.response.status_code} - {e.response.text}"
            ) from e

        # Let TimeoutException and NetworkError propagate directly
        # so that the @retry decorator can catch and retry them.

    async def get_institutions(
        self,
        country_code: str | None = None,
        institution_type: str | None = None,
        per_page: int = 200,
        cursor: str | None = None,
        mailto: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch institutions from OpenAlex.

        Args:
            country_code: Filter by country code (e.g., 'US', 'CN')
            institution_type: Filter by type (e.g., 'education')
            per_page: Number of results per page (max 200)
            cursor: Cursor for pagination
            mailto: Email for polite API

        Returns:
            API response with institutions list and meta info
        """
        params = {
            "per_page": min(per_page, 200),
        }

        # Build filter query
        filters = []
        if country_code:
            filters.append(f"country_code:{country_code}")
        if institution_type:
            filters.append(f"type:{institution_type}")

        if filters:
            params["filter"] = ",".join(filters)

        if cursor:
            params["cursor"] = cursor

        if mailto or self.email:
            params["mailto"] = mailto or self.email

        return await self._make_request(self.INSTITUTIONS, params)

    async def get_authors(
        self,
        institution_id: str | None = None,
        has_orcid: bool | None = None,
        per_page: int = 200,
        cursor: str | None = None,
        mailto: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch authors from OpenAlex.

        Args:
            institution_id: Filter by institution OpenAlex ID
            has_orcid: Filter by ORCID availability
            per_page: Number of results per page (max 200)
            cursor: Cursor for pagination
            mailto: Email for polite API

        Returns:
            API response with authors list and meta info
        """
        params = {
            "per_page": min(per_page, 200),
        }

        filters = []
        if institution_id:
            filters.append(f"last_known_institutions.id:{institution_id}")
        if has_orcid is not None:
            filters.append(f"has_orcid:{str(has_orcid).lower()}")

        if filters:
            params["filter"] = ",".join(filters)

        if cursor:
            params["cursor"] = cursor

        if mailto or self.email:
            params["mailto"] = mailto or self.email

        return await self._make_request(self.AUTHORS, params)

    async def get_works(
        self,
        author_id: str | None = None,
        per_page: int = 200,
        cursor: str | None = None,
        mailto: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch works from OpenAlex.

        Args:
            author_id: Filter by author OpenAlex ID
            per_page: Number of results per page (max 200)
            cursor: Cursor for pagination
            mailto: Email for polite API

        Returns:
            API response with works list and meta info
        """
        params = {
            "per_page": min(per_page, 200),
        }

        filters = []
        if author_id:
            filters.append(f"author.id:{author_id}")

        if filters:
            params["filter"] = ",".join(filters)

        if cursor:
            params["cursor"] = cursor

        if mailto or self.email:
            params["mailto"] = mailto or self.email

        return await self._make_request(self.WORKS, params)

    async def get_author_by_id(self, author_id: str) -> dict[str, Any]:
        """
        Fetch a single author by OpenAlex ID.

        Args:
            author_id: OpenAlex author ID (e.g., 'A1234567890')

        Returns:
            Author data
        """
        return await self._make_request(f"{self.AUTHORS}/{author_id}")

    async def get_institution_by_id(self, institution_id: str) -> dict[str, Any]:
        """
        Fetch a single institution by OpenAlex ID.

        Args:
            institution_id: OpenAlex institution ID (e.g., 'I1234567890')

        Returns:
            Institution data
        """
        return await self._make_request(f"{self.INSTITUTIONS}/{institution_id}")

    async def iterate_institutions(
        self,
        country_code: str | None = None,
        institution_type: str | None = None,
        max_records: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Iterate through all institutions with pagination.

        Args:
            country_code: Filter by country code
            institution_type: Filter by type
            max_records: Maximum number of records to fetch

        Yields:
            Individual institution records
        """
        cursor = None
        count = 0

        while True:
            response = await self.get_institutions(
                country_code=country_code,
                institution_type=institution_type,
                cursor=cursor,
            )

            results = response.get("results", [])
            if not results:
                break

            for institution in results:
                yield institution
                count += 1
                if max_records and count >= max_records:
                    return

            # Get next cursor
            meta = response.get("meta", {})
            cursor = meta.get("next_cursor")
            if not cursor:
                break

    async def iterate_authors(
        self,
        institution_id: str | None = None,
        max_records: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Iterate through all authors with pagination.

        Args:
            institution_id: Filter by institution
            max_records: Maximum number of records to fetch

        Yields:
            Individual author records
        """
        cursor = None
        count = 0

        while True:
            response = await self.get_authors(
                institution_id=institution_id,
                cursor=cursor,
            )

            results = response.get("results", [])
            if not results:
                break

            for author in results:
                yield author
                count += 1
                if max_records and count >= max_records:
                    return

            meta = response.get("meta", {})
            cursor = meta.get("next_cursor")
            if not cursor:
                break

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> OpenAlexClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()


# Convenience function
def get_openalex_client() -> OpenAlexClient:
    """Get configured OpenAlex client instance."""
    return OpenAlexClient(
        email=settings.OPENALEX_EMAIL,
        rate_limit=settings.OPENALEX_RATE_LIMIT,
    )
