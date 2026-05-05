# 开源人才库系统 — 健康度CT扫描总览报告

> 扫描时间：2026-05-05  
> 扫描范围：`backend/app/` (~182 .py) + `frontend/src/` (~60 .ts/.tsx) + 部署配置  
> 扫描方法：静态分析 + 深度代码阅读 + SRE 检查清单

---

## 项目健康度评分：55/100

```
┌─────────────────────────────────────────────────────────┐
│  架构分层合规    ████████████████░░░░░░  15/20          │
│  依赖健康度      ███████████████░░░░░░░  15/15 ✅       │
│  代码规模控制    █████░░░░░░░░░░░░░░░░░   5/15          │
│  函数质量        █████░░░░░░░░░░░░░░░░░   5/10          │
│  错误处理规范    █████░░░░░░░░░░░░░░░░░   5/10          │
│  采集链路韧性    █████░░░░░░░░░░░░░░░░░   5/20          │
│  可观测性        █████░░░░░░░░░░░░░░░░░   5/10          │
└─────────────────────────────────────────────────────────┘
                        总分：55/100
```

### 评分说明

| 维度 | 满分 | 得分 | 扣分原因 |
|------|------|------|---------|
| 架构分层合规 | 20 | 15 | 6 处跨层穿透（Endpoint→Model/Collector） |
| 依赖健康度 | 15 | 15 | 无循环依赖，Repository 层保持纯净 ✅ |
| 代码规模控制 | 15 | 5 | 49 个巨型文件（>300行），最大 1188 行 |
| 函数质量 | 10 | 5 | 22 个过长函数（>100行），最大 1078 行 |
| 错误处理规范 | 10 | 5 | 同文件内 logger.error / raise / return dict 混用 |
| 采集链路韧性 | 20 | 5 | 429 不重试、无全局事务、无熔断、无幂等 |
| 可观测性 | 10 | 5 | 有请求日志但无 traceId 传递、无 Prometheus 指标 |

---

## Top 10 必须立即修复的问题

### 🔴 P0 级（本周内修复）

| # | 问题 | 文件路径 | 行号 | 风险 |
|---|------|---------|------|------|
| 1 | **OpenAlex 429 不自动重试** | [`app/services/openalex_client.py`](../../backend/app/services/openalex_client.py) | L127-128 | 采集任务频繁因限流失败 |
| 2 | **GitHub 超时不在重试范围** | [`app/services/open_source/github_client.py`](../../backend/app/services/open_source/github_client.py) | L120-125 | 偶发超时直接中断采集 |
| 3 | **GitHub 采集单事务过大** | [`app/services/open_source/collectors/github_collector.py`](../../backend/app/services/open_source/collectors/github_collector.py) | L131-151 | 单个 contributor 失败导致全部回滚 |
| 4 | **跨 Phase 无全局事务** | [`app/services/collect/orchestrator.py`](../../backend/app/services/collect/orchestrator.py) | L165-182 | 某 Phase 失败后数据不一致 |
| 5 | **Endpoint 直接 import Model** | [`app/api/v1/endpoints/open_source.py`](../../backend/app/api/v1/endpoints/open_source.py) | L21-22 | 跨层穿透，架构脆弱 |
| 6 | **函数内延迟 import Collector** | [`app/api/v1/endpoints/collect.py`](../../backend/app/api/v1/endpoints/collect.py) | L94, L657 | 循环依赖 workaround，需重构 Service 层 |

### 🟡 P1 级（本月内修复）

| # | 问题 | 文件路径 | 行号 | 风险 |
|---|------|---------|------|------|
| 7 | **`_is_postgres` 函数 502 行** | [`app/repositories/embedding_repository.py`](../../backend/app/repositories/embedding_repository.py) | L32 | 维护困难，圈复杂度高 |
| 8 | **自建 411 行重试逻辑** | [`app/services/data_fetchers.py`](../../backend/app/services/data_fetchers.py) | L52-69 | tenacity 已存在，重复造轮子 |
| 9 | **每次请求新建 HTTP Client** | [`app/services/openalex_client.py`](../../backend/app/services/openalex_client.py) | L180-181 | 无连接池复用，资源浪费 |
| 10 | **硬编码 OpenAlex API URL** | [`app/api/v1/endpoints/system_config.py`](../../backend/app/api/v1/endpoints/system_config.py) | L654 | 配置与代码耦合 |

---

## 修复优先级时间线

### 本周（P0 架构安全）

1. [ ] 修复 OpenAlex 429 自动重试（读取 `Retry-After`，等待后重试）
2. [ ] 将 `httpx.TimeoutException` 加入 GitHub Client 重试范围
3. [ ] GitHub 采集改为每个 contributor 独立事务（或 savepoint）
4. [ ] 为采集编排器引入 Saga/补偿事务模式
5. [ ] 将 Endpoint 中的 Model import 迁移到 Service/Repository 层
6. [ ] 消除 `collect.py` 中的延迟 import，通过 Service 封装 Collector

### 本月（P1 代码质量）

7. [ ] 拆分巨型文件（`talent_repository.py` → 按查询类型拆分）
8. [ ] 拆分过长函数（`SearchRecommendPage` 1078 行 → 子组件）
9. [ ] 用 `tenacity` 替换 `data_fetchers.py` 中的自定义重试装饰器
10. [ ] `openalex_client.py` 复用 `HttpClientFactory`，避免每次新建 client
11. [ ] 封装统一的错误处理装饰器（替代 60+ 处重复的 `except Exception + logger.error`）
12. [ ] 提取 API URL 到配置常量（`GITHUB_BASE_URL`、`OPENALEX_BASE_URL`）

### 季度（P2 可观测性与优化）

13. [ ] 引入 Prometheus 指标暴露（采集成功率、API 延迟 P99、队列堆积数）
14. [ ] 采集链路 traceId 传递（将 `request.state.request_id` 注入采集日志）
15. [ ] 引入断路器（`pybreaker`），防止 API 故障雪崩
16. [ ] 清理前端死代码（`useQueries.ts` 中 10+ 个未使用 Hook）
17. [ ] 引入运行时覆盖率工具，识别后端真实死代码
18. [ ] 增加采集任务幂等性保证（幂等键：repo + commit_sha）

---

## 各阶段报告索引

| 阶段 | 报告 | 核心结论 |
|------|------|---------|
| 阶段1 | [`01-dependency-graph.md`](01-dependency-graph.md) | 6 处跨层穿透，无循环依赖，Repository 层纯净 |
| 阶段2 | [`02-code-smell-heatmap.md`](02-code-smell-heatmap.md) | 49 个巨型文件，22 个过长函数，60+ 处重复代码 |
| 阶段3 | [`03-ai-style-markers.md`](03-ai-style-markers.md) | 硬编码魔法值散落，错误处理风格混乱，无意义注释 |
| 阶段4 | [`04-pipeline-resilience.md`](04-pipeline-resilience.md) | 429 不重试、无全局事务、无熔断、无幂等 |

---

## 总体评估

**优势** ✅
- 分层架构设计合理（Endpoint → Service → Repository → Model）
- 无循环依赖，模块边界清晰
- 命名风格统一（前后端各有规范）
- 已具备基础的重试和限流机制
- 任务进度追踪完善（11 阶段 + 百分比）

**劣势** ⚠️
- 跨层穿透破坏了分层隔离性
- 采集链路韧性薄弱（无熔断、无全局事务、无幂等）
- 代码规模失控（近 1/3 文件超过 300 行）
- 错误处理风格混乱（同一文件内 3 种模式混用）
- 可观测性不足（无 Prometheus、traceId 未传递）

**建议**：优先修复采集链路的 P0 问题（429 重试 + 事务），这是系统的核心命脉；代码规模问题可通过持续重构逐步改善。
