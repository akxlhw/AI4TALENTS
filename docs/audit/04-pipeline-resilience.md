# 阶段4：数据采集链路单点故障分析（重点）

> 扫描时间：2026-05-05  
> 扫描范围：GitHub API → OpenAlex API → 数据清洗 → 本地存储  
> 方法：深度代码阅读 + SRE 检查清单

---

## 一、GitHub API 采集链路

### 1.1 链路概览

```
Endpoint (trigger collect)
    ↓
github_client.py  ←→  GitHub REST API
    ↓
github_collector.py
    ↓
SyncService (upsert_developer / upsert_repository / upsert_contribution)
    ↓
PostgreSQL (os_developer, os_repository, os_contribution)
```

### 1.2 重试机制

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 指数退避重试 | ✅ 有 | — | `tenacity.wait_exponential(multiplier=1, min=2, max=30)` |
| 最大重试次数 | ✅ 有 | — | `stop_after_attempt(3)` |
| 重试异常范围 | ⚠️ 部分 | P1 | 仅重试 `HTTPStatusError` + `NetworkError`，**不覆盖 `httpx.TimeoutException`** |
| 降级策略 | ❌ 无 | P1 | 除 404 返回空 dict 外，无其他降级（如跳过该 contributor） |

**关键代码**：[`github_client.py`](../../backend/app/services/open_source/github_client.py) L120-158

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

> **风险**：`httpx.TimeoutException` 不在重试范围内，GitHub API 超时会直接抛异常中断采集。

### 1.3 熔断与限流

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 主动限流（请求间隔） | ✅ 有 | — | `_min_interval = 0.2`（200ms），通过 `_throttle()` 控制 |
| Rate Limit 响应头读取 | ✅ 有 | — | 读取 `X-RateLimit-Remaining` 和 `X-RateLimit-Reset` |
| 多 Token 轮换 | ✅ 有 | — | 支持多个 GitHub Token 自动切换 |
| Token 耗尽等待 | ✅ 有 | — | 所有 Token 耗尽后，等待至 `X-RateLimit-Reset`（上限 1 小时） |
| 熔断机制 | ❌ 无 | P1 | 连续失败不会触发熔断，会持续重试直到 Token 耗尽 |

**关键代码**：[`github_client.py`](../../backend/app/services/open_source/github_client.py) L134-155

> **风险**：无熔断。如果 GitHub API 出现区域性故障，系统会持续重试所有 Token，每次等待 1 小时，采集队列会严重堆积。

### 1.4 事务与一致性

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 单条 contributor 事务 | ❌ 无 | P0 | 整个仓库的 contributor 处理在一个 `async with AsyncSessionLocal()` 中 |
| 失败隔离 | ⚠️ 部分 | P1 | 单个 contributor 失败被 `try/except` 吞掉，但**不标记失败记录** |
| 脏写风险 | ⚠️ 有 | P1 | 第 90-98 行单独开了一个 session 更新 `os_repo_config.stars_count`，无事务一致性 |
| 幂等性 | ❌ 无 | P1 | 重复执行同一采集任务会重复插入/更新数据 |
| 部分字段缺失 | ✅ 容错 | — | `user.get("email") or ""` 等模式能处理空值 |

**关键代码**：[`github_collector.py`](../../backend/app/services/open_source/collectors/github_collector.py) L90-98

```python
# 独立的 session，无事务关联
async with AsyncSessionLocal() as session:
    config = await session.scalar(...)
    if config:
        config.stars_count = stars
        await session.commit()  # ← 即使后续 contributor 处理失败，stars_count 已更新
```

> **风险**：如果 contributor 采集过程中失败，`os_repo_config.stars_count` 已被更新但数据不完整，导致不一致。

### 1.5 可观测性

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 结构化日志 | ⚠️ 部分 | P1 | 有 `logger.info/warning/error`，但**无 traceId** |
| 请求耗时记录 | ❌ 无 | P2 | 未记录单次 GitHub API 调用耗时 |
| 任务进度追踪 | ✅ 有 | — | `OSCollectTask` 表有 `progress_percent`, `current_step` |
| 失败上下文 | ⚠️ 部分 | P1 | contributor 失败时只记录 `logger.warning(f"Failed to process contributor {login}: {e}")`，**无 repo_name、task_id** |
| 监控指标 | ❌ 无 | P2 | 无 Prometheus 指标暴露采集成功率、API P99 延迟 |

---

## 二、OpenAlex API 采集链路

### 2.1 链路概览

```
Endpoint (trigger collect)
    ↓
CollectionOrchestrator
    ↓
WorkFetcher / AuthorFetcher / InstitutionFetcher
    ↓
openalex_client.py / data_fetchers.py  ←→  OpenAlex API
    ↓
RawWork / RawAuthor / RawInstitution
    ↓
Normalizers
    ↓
StdAuthor / StdSchool
    ↓
SyncService
    ↓
Talent / School (Serving Layer)
```

### 2.2 重试机制

#### OpenAlexClient (`openalex_client.py`)

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 指数退避重试 | ✅ 有 | — | `tenacity.wait_exponential(multiplier=1, min=1, max=10)` |
| 最大重试次数 | ✅ 有 | — | `stop_after_attempt(3)` |
| 重试异常范围 | ⚠️ 部分 | P1 | 仅重试 `TimeoutException` + `NetworkError`，**不覆盖 HTTP 5xx** |
| 429 处理 | ❌ 无重试 | P0 | 429 抛 `OpenAlexRateLimitError`，**不自动等待/重试** |
| 降级策略 | ❌ 无 | P1 | 无降级 |

**关键代码**：[`openalex_client.py`](../../backend/app/services/openalex_client.py) L91-137

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
)
async def _make_request(...):
    ...
    if e.response.status_code == 429:
        raise OpenAlexRateLimitError("Rate limit exceeded") from e  # ← 直接抛出，不重试
```

> **风险**：OpenAlex 返回 429 时任务直接失败，不会等待后重试。

#### DataFetchers (`data_fetchers.py`)

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 自定义重试装饰器 | ✅ 有 | — | `with_retry(max_attempts=5, max_wait=60.0)` |
| 429 处理 | ✅ 有 | — | 抛 `RetryableError`，触发重试 |
| 5xx 处理 | ✅ 有 | — | 也抛 `RetryableError`，触发重试 |
| 4xx 处理 | ❌ 无重试 | P1 | 非 200/429/5xx 直接 `raise Exception`，**不触发重试** |

**关键代码**：[`data_fetchers.py`](../../backend/app/services/data_fetchers.py) L131-140

```python
if response.status == 429:
    raise RetryableError("Rate limited (HTTP 429)")
if response.status >= 500:
    raise RetryableError(f"Server error (HTTP {response.status})")
if response.status != 200:
    raise Exception(f"HTTP {response.status}")  # ← 4xx 错误不重试
```

> **风险**：OpenAlex 返回 400（参数错误）或 404（资源不存在）时直接失败，可能导致整批数据丢失。

### 2.3 熔断与限流

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 请求速率限制 | ✅ 有 | — | `rate_limit = 10` req/s，`_async_wait_for_rate_limit()` |
| 熔断机制 | ❌ 无 | P1 | 无 |
| 并发控制 | ❌ 无 | P1 | 无 semaphore/队列限制 |

> **风险**：无并发控制。如果同时触发多个采集任务，可能瞬间压满 OpenAlex 限流。

### 2.4 事务与一致性

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 单 Phase 事务 | ⚠️ 部分 | P1 | 每个 PhaseHandler 内部有 session，但 Orchestrator 不统一管理 |
| 跨 Phase 一致性 | ❌ 无 | P0 | Phase 1-11 各自独立，**无全局事务** |
| 失败回滚 | ❌ 无 | P0 | 某 Phase 失败后，前面 Phase 的数据已写入，不会回滚 |
| 幂等性 | ❌ 无 | P1 | 重复执行同一任务会重复处理数据 |
| 脏写风险 | ✅ 有 | — | `orchestrator.py` L176-178：Phase 1 中途更新 `task.total_records` 并 `commit` |

**关键代码**：[`orchestrator.py`](../../backend/app/services/collect/orchestrator.py) L165-182

```python
for handler in self._handlers:
    result = await handler.execute(context)
    if isinstance(handler, PhaseCollectHandler):
        task.total_records = progress.total_works
        await self.session.commit()  # ← 中途 commit
```

> **风险**：Phase 1 提交后，如果 Phase 2 失败，Phase 1 的原始数据已写入，形成脏数据。

### 2.5 可观测性

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| 结构化日志 | ⚠️ 部分 | P1 | ProgressTracker 有日志，但**无 traceId** |
| 请求耗时记录 | ❌ 无 | P2 | 未记录单次 OpenAlex API 调用耗时 |
| 队列堆积监控 | ❌ 无 | P2 | 无采集队列长度指标 |
| 任务进度 | ✅ 有 | — | 11 个 Phase 均有进度百分比 |
| 错误详情 | ✅ 有 | — | `traceback.format_exc()` 被记录到 `progress.errors` |

---

## 三、HTTP 客户端工厂层

| 检查项 | GitHub 客户端 | OpenAlex 客户端 | 评估 |
|--------|--------------|-----------------|------|
| 统一工厂创建 | ✅ `HttpClientFactory` | ❌ 直接 `httpx.AsyncClient` | OpenAlex 未复用工厂 |
| 代理支持 | ✅ 有 | ⚠️ 部分 | OpenAlex 有 `get_proxy_for_request`，但 `openalex_client.py` 未使用 |
| 连接池复用 | ✅ 有 | ❌ 无 | `openalex_client.py` 每次请求新建 client |

> **资源风险**：`openalex_client.py` 每次 `_make_request` 都新建 `httpx.AsyncClient`，无连接池复用，高并发时会产生大量 TCP 连接开销。

---

## 四、API 网关层（可观测性）

### 4.1 Request Logging Middleware

**关键代码**：[`middleware/request_logging.py`](../../backend/app/middleware/request_logging.py)

```python
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(..., extra={"request_id": request_id, ...})
        response.headers["X-Request-ID"] = request_id
```

| 检查项 | 当前状态 | 风险等级 | 详情 |
|--------|---------|---------|------|
| Request ID | ✅ 有 | — | 每个请求生成 8 位 UUID，存入 `request.state` |
| 耗时记录 | ✅ 有 | — | 记录处理时间（毫秒） |
| 状态码记录 | ✅ 有 | — | 记录响应状态码 |
| traceId 传递 | ❌ 无 | P1 | Request ID **未传递**到采集链路（GitHub/OpenAlex 调用未携带） |
| 采集链路关联 | ❌ 无 | P2 | 采集任务日志与 HTTP 请求日志无关联 |

---

## 五、风险汇总与修复建议

### P0 级风险（立即修复）

| # | 风险 | 影响 | 修复建议 |
|---|------|------|---------|
| 1 | OpenAlex 429 不自动重试 | 采集任务频繁因限流失败 | 在 `_make_request` 中捕获 429，读取 `Retry-After` 头，等待后重试 |
| 2 | 跨 Phase 无全局事务 | 某 Phase 失败后数据不一致 | 引入 Saga 模式或补偿事务，失败时标记脏数据并触发清理 |
| 3 | GitHub 采集单 session 处理全部 contributor | 单个 contributor 失败导致整个 session 可能回滚 | 每个 contributor 使用独立事务 |

### P1 级风险（本月修复）

| # | 风险 | 影响 | 修复建议 |
|---|------|------|---------|
| 1 | 无熔断机制 | API 故障时雪崩 | 引入 `pybreaker` 或自研断路器，连续失败 N 次后快速失败 |
| 2 | `openalex_client.py` 每次新建 client | 连接开销大 | 复用 `HttpClientFactory` 或 session 级别的 client |
| 3 | GitHub 超时不重试 | 偶发超时导致任务失败 | 将 `httpx.TimeoutException` 加入重试范围 |
| 4 | 采集链路无 traceId | 问题定位困难 | 将 `request.state.request_id` 传递到采集日志中 |
| 5 | 无幂等性保证 | 重复任务产生重复数据 | 采集任务增加幂等键（如 `repo_full_name + commit_sha`） |
| 6 | `os_repo_config.stars_count` 独立更新 | 与 contributor 数据不一致 | 将 stars 更新移入同一事务，或改为异步后台任务 |

### P2 级风险（季度优化）

| # | 风险 | 影响 | 修复建议 |
|---|------|------|---------|
| 1 | 无 Prometheus 指标 | 无法监控采集健康度 | 暴露 `collection_success_rate`, `github_api_latency_p99` 等指标 |
| 2 | 无采集队列堆积监控 | 任务积压无感知 | 暴露 `collect_queue_size`, `collect_task_wait_time` 指标 |
| 3 | 单次 API 调用无耗时记录 | 性能瓶颈难定位 | 在 `_get` 和 `_make_request` 中记录请求耗时 |
| 4 | 无并发控制 | 高并发压垮外部 API | 引入 `asyncio.Semaphore` 限制并发数 |

---

> 下一步：等待用户确认后，生成最终 `SUMMARY.md` 总览报告。
