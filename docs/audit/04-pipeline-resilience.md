# Phase 4: 数据采集链路单点故障分析 (v2.0.1 更新)

> 扫描时间：2026-05-12

## 采集链路总览

```
GitHub API / OpenAlex API
    ↓ (retry + rate limit)
Data Fetching (data_fetchers.py / github_collector.py)
    ↓ (batch upsert + error catch)
Normalization (normalizers/author.py, school.py)
    ↓ (per-record isolation)
Sync (sync/author_sync.py, school_sync.py)
    ↓ (phase commit + checkpoint)
Serving (core_talent)
```

---

## 1. 重试机制

| 组件 | 指数退避 | 最大重试 | 重试谓词 | 失败后 | 评级 |
|------|---------|---------|---------|--------|------|
| OpenAlex Client | ✅ `wait_exponential(1,1,10)` + Retry-After | ✅ 5次 | ✅ 仅 Timeout/Network/429 | 异常上抛 | B |
| OpenAlex Works Fetcher | ✅ `wait_exponential(1,1,60)` | ✅ 5次 | ✅ 429/5xx→RetryableError | 标记failed继续 | A |
| OpenAlex Author/Inst Fetcher | ❌ 无 | ❌ 无 | ❌ 无 | 整批丢失 | **D** |
| GitHub Client | ✅ `wait_exponential(1,2,30)` | ✅ 3次 | ✅ Network/Timeout/429/5xx | 异常上抛 | A |
| HTTP Client Factory | ❌ 无 | ❌ 无 | ❌ 无 | N/A | C |

### 🔴 P1: Author/Institution 批量获取无重试

`data_fetchers.py:600-673` (authors) 和 `717-778` (institutions) 的 fetcher 循环中：
- Works fetcher 有 `_fetch_page_with_retry` 封装
- Author/Institution fetcher **没有**，仅在 batch 级别 catch 异常 → `progress.failed += len(batch)` → 静默跳过

**影响**: 一次瞬时 429 或 5xx 错误会丢失整个批次 (25个 author/institution)。

---

## 2. 限流与并发控制

| 组件 | 限流方式 | 并发控制 | 评级 |
|------|---------|---------|------|
| GitHub Client | ✅ 多 Token 轮换 + X-RateLimit-Remaining 追踪 | ✅ 全局 Semaphore(1) | A |
| OpenAlex Client | ✅ min_interval 节流 + Retry-After 遵从 | ❌ 无 Semaphore | B |
| 全局熔断器 | ❌ 无 | N/A | **D** |

### 🟡 P1: 无熔断器

当 GitHub/OpenAlex 持续故障时，所有采集任务会反复重试直到超时，没有 fail-fast 机制。应在连续 N 次失败后触发熔断，暂停一段时间再尝试。

---

## 3. 事务与一致性

| 组件 | 事务策略 | 一致性 | 评级 |
|------|---------|--------|------|
| Orchestrator | ✅ Phase 级 commit + checkpoint | ✅ 关键/非关键 Phase 分离 | A |
| Author Normalizer | ✅ per-record 隔离 + failed 标记 | ✅ 坏记录不污染批次 | A |
| School Normalizer | ⚠️ per-record 隔离 | ❌ 失败记录未标记为 failed | **C** |
| Sync Services | ✅ flush only, Orchestrator commit | ✅ 无独立 commit | A |

### 🔴 P1: School Normalizer 失败记录无限重试

`school.py:223-224`: 失败的 raw_institution 仅 `result.failed += 1`，不调用 `batch_mark_processed(failed_ids, "failed")`。结果：失败记录永远留在 "pending"，每次管道运行都会重新尝试处理同一条永久损坏的记录。

### 🟡 P1: Venue 子任务无游标级断点

Orchestrator 有 Phase 级 checkpoint，但 venue 子任务内部无游标级断点。如果一个有 10,000 篇论文的 venue 在第 8,000 篇时崩溃，下次重试从头开始。

---

## 4. 可观测性

| 能力 | 状态 | 详情 |
|------|------|------|
| HTTP 请求 ID | ✅ | `RequestLoggingMiddleware` 生成 UUID |
| 后台任务关联 | ❌ | `request_id` 不传播到 `asyncio.create_task` |
| Prometheus HTTP 指标 | ✅ | counter/histogram/gauge 齐全 |
| 管道专属指标 | ⚠️ | 仅有粗粒度 `collection_tasks_*` |
| Phase 级日志 | ✅ | `ProgressTracker` 结构化存储 |

### 🟡 P1: 后台任务无关联 ID

采集任务通过 `BackgroundTasks` / `asyncio.create_task` 运行，`request_id` 无法从 HTTP 请求传播到后台任务。日志中无法将采集错误关联到触发请求或用户。

---

## P1 风险清单

| # | 风险 | 当前状态 | 位置 | 修复建议 |
|---|------|---------|------|---------|
| 1 | Author/Inst 批量获取无重试 | 无 | `data_fetchers.py:600-778` | 复用 `_fetch_page_with_retry` 模式 |
| 2 | 无熔断器 | 无 | 全局 | 引入 circuit breaker 装饰器 |
| 3 | School 正常化器失败记录未标记 | 部分 | `school.py:223` | 添加 `batch_mark_processed(failed, "failed")` |
| 4 | 子任务无游标级断点 | 无 | `venue_executor.py` | 记录 cursor position 到 sub_task |
| 5 | 后台任务无关联 ID | 无 | `collect.py` | 传递 request_id 到 create_task |
