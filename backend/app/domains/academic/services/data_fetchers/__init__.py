"""
OpenAlex data fetchers for the raw data layer.
OpenAlex 数据采集器 - 负责从 API 获取数据并存入原始数据层

本包由原 data_fetchers.py 单体拆分而来：
- common.py: 重试/熔断/上游指标等公共逻辑与 OpenAlexClient 配置
- work_fetcher.py: WorkFetcher（论文采集）
- author_fetcher.py: AuthorFetcher（作者采集）与 extract_institutions
- institution_fetcher.py: InstitutionFetcher（机构采集）

原模块的公共接口经此 __init__ 原样 re-export，调用方零改动。
"""

from app.domains.academic.services.data_fetchers.author_fetcher import (
    AuthorFetcher,
    extract_institutions,
)
from app.domains.academic.services.data_fetchers.common import (
    DEFAULT_TIMEOUT,
    MAX_WORKS_PER_VENUE,
    RETRY_AFTER_MAX_WAIT,
    OpenAlexClient,
    RetryableError,
    _openalex_fetcher_breaker,
    _parse_retry_after,
    _rate_limited_error,
    _record_upstream,
    _wait_honoring_retry_after,
    with_retry,
)
from app.domains.academic.services.data_fetchers.institution_fetcher import InstitutionFetcher
from app.domains.academic.services.data_fetchers.work_fetcher import WorkFetcher

__all__ = [
    "MAX_WORKS_PER_VENUE",
    "DEFAULT_TIMEOUT",
    "RETRY_AFTER_MAX_WAIT",
    "RetryableError",
    "with_retry",
    "OpenAlexClient",
    "WorkFetcher",
    "AuthorFetcher",
    "InstitutionFetcher",
    "extract_institutions",
    "_openalex_fetcher_breaker",
    "_parse_retry_after",
    "_rate_limited_error",
    "_record_upstream",
    "_wait_honoring_retry_after",
]
