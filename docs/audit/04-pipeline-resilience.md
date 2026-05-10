# 阶段4：数据采集链路单点故障分析 (v2.0.0 更新)

> 扫描时间：2026-05-09
> 扫描范围：GitHub API → OpenAlex API → 数据清洗 → 本地存储
> 方法：深度代码阅读 + SRE 检查清单

---

## 一、GitHub API 采集链路

### 1.1 链路概览

```
open_source/api/open_source.py (trigger collect)
    ↓
open_source/services/collectors/github_collector.py
    ↓
open_source/services/github_client.py  ←→  GitHub REST API
    ↓
open_source/services/collectors/sync_service.py (upsert)
    ↓
PostgreSQL (os_developer, os_repository, os_contribution)
```

### 1.2 重试机制

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 指数退避重试 | ✅ 有 | — | `tenacity.wait_exponential(multiplier=1, min=2, max=30)` |
| 最大重试次数 | ✅ 有 | — | `stop_after_attempt(3)` |
| 重试异常范围 | ⚠️ 部分 | P1 | 仅重试 `HTTPStatusError` + `NetworkError`，**不覆盖 `httpx.TimeoutException`** |
| 降级策略 | ❌ 无 | P1 | 除 404 返回空 dict 外无降级 |

**关键代码**: `open_source/services/github_client.py` L120-158

```python
@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.NetworkError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def _get(self, path: str, ...) -> Any:
    ...
    if response.status_code == 404:
        return {}  # ← 唯一降级
```

> **P1 风险**: `httpx.TimeoutException` 不在重试范围，GitHub API 超时会直接抛异常中断采集。

### 1.3 熔断与限流

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 主动限流（请求间隔） | ✅ 有 | — | `_min_interval = 0.2`（200ms），`_throttle()` |
| Rate Limit 响应头读取 | ✅ 有 | — | 读取 `X-RateLimit-Remaining` 和 `X-RateLimit-Reset` |
| 多 Token 轮换 | ✅ 有 | — | 支持多个 GitHub Token 自动切换 |
| Token 耗尽等待 | ✅ 有 | — | 所有 Token 耗尽后等待至 Reset（上限 1 小时）|
| 熔断机制 | ❌ 无 | P1 | 连续失败不会触发熔断 |

> **P1 风险**: 无熔断器。GitHub API 区域性故障时，系统会持续尝试所有 Token。

### 1.4 事务与一致性

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 单条 contributor 事务 | ❌ 无 | P0 | 整个仓库 contributor 处理在一个 session 中 |
| 失败隔离 | ⚠️ 部分 | P1 | 单个 contributor 失败被 `try/except` 吞掉，但**不标记失败记录** |
| Stars 独立更新 | ⚠️ 有 | P1 | `os_repo_config.stars_count` 在独立 session 中更新 |
| 幂等性 | ❌ 无 | P1 | 重复执行同一采集任务会重复处理 |
| 部分字段缺失 | ✅ 容错 | — | `user.get("email") or ""` 能处理空值 |

> **P0 风险**: 如果 contributor 采集过程中失败，`stars_count` 已更新但数据不完整。

### 1.5 可观测性

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 结构化日志 | ⚠️ 部分 | P1 | 有 `logger.info/warning/error`，但**无 traceId** |
| 请求耗时记录 | ❌ 无 | P2 | 未记录单次 API 调用耗时 |
| 任务进度追踪 | ✅ 有 | — | `OSCollectTask` 表有 `progress_percent`、`current_step` |
| 失败上下文 | ⚠️ 部分 | P1 | contributor 失败只记录 `logger.warning(f"Failed...{login}: {e}")` |
| 监控指标 | ❌ 无 | P2 | 无 Prometheus 指标暴露采集成功率 |

---

## 二、OpenAlex API 采集链路

### 2.1 链路概览

```
academic/api/collect.py (trigger)
    ↓
academic/services/collect/orchestrator.py (CollectionOrchestrator)
    ↓
academic/services/collect/phases/phase_1_collect.py (WorkFetcher)
academic/services/collect/phases/phase_2_fetch_authors.py (AuthorFetcher)
academic/services/collect/phases/phase_3_fetch_institutions.py (InstitutionFetcher)
    ↓
academic/services/openalex_client.py / data_fetchers.py  ←→  OpenAlex API
    ↓
raw_work / raw_author / raw_institution
    ↓
academic/services/normalizers/ (author.py, school.py, tech_belong.py)
    ↓
std_author / std_school
    ↓
academic/services/sync/ (author_sync.py, school_sync.py)
    ↓
core_talent / core_school (Serving Layer)
```

### 2.2 重试机制

#### OpenAlexClient (`academic/services/openalex_client.py`)

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 指数退避重试 | ✅ 有 | — | `tenacity.wait_exponential(multiplier=1, min=1, max=10)` |
| 最大重试次数 | ✅ 有 | — | `stop_after_attempt(3)` |
| 重试异常范围 | ⚠️ 部分 | P1 | 仅重试 `TimeoutException` + `NetworkError`，**不覆盖 HTTP 5xx** |
| 429 处理 | ❌ 无重试 | **P0** | 429 抛 `OpenAlexRateLimitError`，**不自动等待/重试** |
| 降级策略 | ❌ 无 | P1 | 无降级 |

> **P0 风险**: OpenAlex 返回 429 时任务直接失败，不会等待 Retry-After 后重试。

#### DataFetchers (`academic/services/data_fetchers.py`)

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 自定义重试装饰器 | ✅ 有 | — | `with_retry(max_attempts=5, max_wait=60.0)` |
| 429 处理 | ✅ 有 | — | 抛 `RetryableError`，触发重试 |
| 5xx 处理 | ✅ 有 | — | 抛 `RetryableError`，触发重试 |
| 4xx 处理 | ❌ 无重试 | P1 | 非 200/429/5xx 直接 `raise Exception` |

### 2.3 熔断与限流

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 请求速率限制 | ✅ 有 | — | `rate_limit = 10` req/s |
| 熔断机制 | ❌ 无 | P1 | 无 |
| 并发控制 | ❌ 无 | P1 | 无 semaphore/队列限制 |

### 2.4 事务与一致性

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 单 Phase 事务 | ⚠️ 部分 | P1 | 每个 PhaseHandler 内部有 session，Orchestrator 不统一管理 |
| 跨 Phase 一致性 | ❌ 无 | **P0** | Phase 1-11 各自独立，**无全局事务** |
| 失败回滚 | ❌ 无 | **P0** | 某 Phase 失败后，前面 Phase 的数据已写入，不会回滚 |
| 幂等性 | ❌ 无 | P1 | 重复执行同一任务会重复处理数据 |
| 中途 commit | ⚠️ 有 | P1 | Phase 1 中途更新 `task.total_records` 并 commit |

> **P0 风险**: Phase 1 提交后，如果 Phase 2 失败，Phase 1 的脏数据留在数据库中。

### 2.5 可观测性

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 结构化日志 | ⚠️ 部分 | P1 | ProgressTracker 有日志，但**无 traceId** |
| 请求耗时记录 | ❌ 无 | P2 | 未记录单次 API 调用耗时 |
| 任务进度 | ✅ 有 | — | 11 个 Phase 均有进度百分比 |
| 错误详情 | ✅ 有 | — | `traceback.format_exc()` 记录到 `progress.errors` |
| Prometheus 指标 | ⚠️ 部分 | P2 | `core/metrics.py` 存在但采集链路指标未暴露 |

---

## 三、HTTP 客户端层统一性

| 检查项 | GitHub 客户端 | OpenAlex 客户端 | 评估 |
|--------|--------------|-----------------|------|
| 统一工厂创建 | ✅ `HttpClientFactory` | ❌ 直接 `httpx.AsyncClient` | OpenAlex 未复用 |
| 代理支持 | ✅ 有 | ⚠️ 部分 | openalex_client.py 导入了但未使用 |
| 连接池复用 | ✅ 有 | ❌ 无 | 每次请求新建 client |

> **资源风险**: `openalex_client.py` 每次 `_make_request` 都新建 `httpx.AsyncClient`，高并发时 TCP 连接开销大。

---

## 四、API 网关层可观测性

### Request Logging Middleware (`middleware/request_logging.py`)

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| Request ID | ✅ 有 | — | 每个请求生成 8 位 UUID，存入 `request.state` |
| 耗时记录 | ✅ 有 | — | 记录处理时间（毫秒） |
| 状态码记录 | ✅ 有 | — | 记录响应状态码 |
| traceId 传递 | ❌ 无 | P1 | Request ID **未传递**到采集链路 |
| 采集链路关联 | ❌ 无 | P2 | 采集任务日志与 HTTP 请求日志无关联 |

---

## 五、风险汇总

### P0 级（发版前必须修复）

| # | 风险 | 影响 | 修复建议 |
|---|------|------|---------|
| 1 | OpenAlex 429 不自动重试 | 采集任务因限流频繁失败 | 在 `_make_request` 中捕获 429，读取 `Retry-After`，等待后重试 |
| 2 | 跨 Phase 无全局事务 | 某 Phase 失败后数据不一致 | 引入 Saga/补偿事务，失败时标记脏数据并清理 |
| 3 | GitHub 采集单 session 处理全部 contributor | 单 contributor 失败影响全量 | 每个 contributor 使用独立事务或 savepoint |

### P1 级（v2.0.1 修复）

| # | 风险 | 修复建议 |
|---|------|---------|
| 1 | 无熔断机制 | 引入 `pybreaker`，连续失败 N 次后快速失败 |
| 2 | `openalex_client.py` 每次新建 client | 复用 `HttpClientFactory` 或 session 级 client |
| 3 | GitHub 超时不重试 | 将 `httpx.TimeoutException` 加入重试范围 |
| 4 | 采集链路无 traceId | 将 `request.state.request_id` 传递到采集日志 |
| 5 | 无幂等性保证 | 采集任务增加幂等键 |
| 6 | `os_repo_config.stars_count` 独立更新 | 移入同一事务 |

### P2 级（季度优化）

| # | 风险 | 修复建议 |
|---|------|---------|
| 1 | 无采集成功率 Prometheus 指标 | 暴露 `collection_success_rate` 等指标 |
| 2 | 无采集队列堆积监控 | 暴露 `collect_queue_size` 指标 |
| 3 | 单次 API 调用无耗时记录 | 在 `_get`/`_make_request` 中记录耗时 |
| 4 | 无并发控制 | 引入 `asyncio.Semaphore` 限制并发数 |

---

> 关联报告：[01-dependency-graph.md](01-dependency-graph.md) | [02-code-smell-heatmap.md](02-code-smell-heatmap.md) | [03-ai-style-markers.md](03-ai-style-markers.md)
