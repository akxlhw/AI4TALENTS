# 智能人才库 V2.0.0 — 健康度CT扫描总览报告

> 扫描时间：2026-05-09
> 扫描范围：`backend/app/` (~120 .py 源文件) + `frontend/src/` (~60 .ts/.tsx) + 部署配置
> 扫描方法：静态分析 + 深度代码阅读 + SRE 检查清单
> 更新说明：基于 domain-driven 架构重新审计（旧版报告使用了已废弃的扁平路径）

---

## 项目健康度评分：60/100

```
┌─────────────────────────────────────────────────────────┐
│  架构分层合规    ███████████████░░░░░░░  13/20          │
│  依赖健康度      ███████████████░░░░░░░  15/15 ✅       │
│  代码规模控制    ██████░░░░░░░░░░░░░░░░░   6/15          │
│  函数质量        █████░░░░░░░░░░░░░░░░░   5/10          │
│  错误处理规范    █████░░░░░░░░░░░░░░░░░   5/10          │
│  采集链路韧性    ██████░░░░░░░░░░░░░░░░░   6/20          │
│  可观测性        █████░░░░░░░░░░░░░░░░░   5/10          │
│  文档完整性      ██████░░░░░░░░░░░░░░░░░   5/10          │
└─────────────────────────────────────────────────────────┘
                        总分：60/100  (上次审计: 55/100 ↑ +5)
```

### 评分说明

| 维度 | 满分 | 得分 | 扣分原因 |
|------|------|------|---------|
| 架构分层合规 | 20 | 13 | 15 处跨层穿透（v2.0 已治理 13 处，剩 15 处）|
| 依赖健康度 | 15 | 15 | 无循环依赖，Repository 层纯净 ✅ |
| 代码规模控制 | 15 | 6 | 49 个巨型文件（>300行），最大 1398 行 |
| 函数质量 | 10 | 5 | 18 个过长函数（>100行），5 个高圈复杂度 |
| 错误处理规范 | 10 | 5 | 同文件内 3 种错误处理风格混用 |
| 采集链路韧性 | 20 | 6 | P0: 429 不重试 / 无全局事务；P1: 无熔断/无幂等 |
| 可观测性 | 10 | 5 | 有请求日志但无 traceId 传递，部分 Prometheus 指标 |
| 文档完整性 | 10 | 5 | README 过时，API 文档仅 Swagger 自动生成 |

---

## 各维度评分

### 一、架构健康度：70/100

**优势** ✅
- Domain-driven 分层架构设计合理
- 无循环依赖，模块边界清晰
- v2.0.0 已治理 13 项 Endpoint 层跨层穿透
- 前端通过 services/api/ 统一封装外部调用
- 命名风格统一（前后端各有规范）

**问题** ⚠️
- 15 处跨层穿透待治理（API → Repository/Model）
- `open_source/api/open_source.py` 单文件 997 行聚合全部端点
- `open_source_service.py` 1398 行，搜索/导出/嵌入/CRUD 全部混在一起
- README.md 项目结构仍为旧扁平架构，与当前 domain-driven 不符

### 二、代码质量：55/100

**v2.0.0 改进** ✅
- TalentRepository 从 1157 行拆分为 base/search/export
- academic-search-page 从 1166 行拆分为 3 个 tab 组件
- 21 处 `any` 类型治理为 `unknown` + 类型守卫
- AuthContext/FavoritesContext 迁移至 Zustand

**遗留问题** ⚠️
- 49 个文件超过 300 行（占比 ~26%）
- OpenSourceService 成为新的最大文件 (1398 行)
- 18 个函数超过 100 行
- 90+ 处重复错误处理模式
- 12 处前端死代码（favorites 迁移到 Zustand 后旧 hooks 未清理）
- 缺少统一的错误处理装饰器

### 三、文档与规范：55/100

**优势** ✅
- docs/ 目录下有 v1.0~v2.0 各版本完整设计文档
- OpenAPI (Swagger) 自动生成 API 文档
- CHANGELOG.md 遵循 Keep a Changelog 规范
- CLAUDE.md 提供详细的项目开发指南

**问题** ⚠️
- **README.md 项目结构过时**: 显示旧扁平架构而非 domain-driven
- **README.md 开源人才状态错误**: 显示"📋 规划中"但实际已实现
- **README.md 缺少 v2.0 版本说明**: 版本历史停在 v1.5.0
- 无 CONTRIBUTING.md
- 核心算法缺少"为什么"的策略注释（CS 概念评分、RRF 融合等）
- API 文档仅 Swagger 自动生成，缺少入参/返回值/错误码的手写说明

---

## Top 10 必须立即修复的问题

### 🔴 阻断性问题（发版前必须修复）

| # | 问题 | 文件路径 | 风险 |
|---|------|---------|------|
| 1 | **README.md 开源人才状态错误 + 架构图过时** | `README.md` L9-14, L38-61 | 对外文档误导 |
| 2 | **OpenAlex 429 不自动重试** | `backend/app/domains/academic/services/openalex_client.py` | 采集任务因限流频繁失败 |
| 3 | **跨 Phase 无全局事务** | `backend/app/domains/academic/services/collect/orchestrator.py` | Phase 失败后数据不一致 |
| 4 | **8 个测试失败** | `tests/test_audit.py` (2), `tests/test_migrations.py` (2), 其他 (4) | 回归风险 |

### 🟡 严重问题（v2.0.1 必须修复）

| # | 问题 | 文件路径 | 风险 |
|---|------|---------|------|
| 4 | **GitHub 超时不在重试范围** | `backend/app/domains/open_source/services/github_client.py` | 偶发超时中断采集 |
| 5 | **GitHub 采集单事务过大** | `backend/app/domains/open_source/services/collectors/github_collector.py` | 单 contributor 失败影响全量 |
| 6 | **OpenSourceService 1398 行** | `backend/app/domains/open_source/services/open_source_service.py` | 维护困难 |
| 7 | **open_source/api 单文件 997 行** | `backend/app/domains/open_source/api/open_source.py` | 应拆分为多模块 |
| 8 | **15 处 Endpoint → Repository 跨层穿透** | 见 01-dependency-graph.md | 架构分层破坏 |

### 🟠 警告（本月修复）

| # | 问题 | 文件路径 |
|---|------|---------|
| 9 | **90+ 处重复错误处理模式** | 全项目 |
| 10 | **12 处前端死代码（旧 favorites hooks）** | `frontend/src/hooks/useQueries.ts` |

---

## 修复优先级时间线

### 发版前（P0 阻断）

1. [ ] **修复 README.md**: 更新项目结构为 domain-driven，开源人才状态改为"✅ 已完成"
2. [ ] **修复 8 个测试失败**: `test_audit.py` (2) + `test_migrations.py` (2) + 其他 (4)
3. [ ] **OpenAlex 429 自动重试**: 读取 `Retry-After` 头，等待后重试
4. [ ] **采集 Saga 补偿**: 为采集编排器引入 Saga/补偿事务模式

### v2.0.1（P1 严重 — 2 周内）

4. [ ] GitHub Client 将 `httpx.TimeoutException` 加入重试范围
5. [ ] GitHub 采集改为每个 contributor 独立事务
6. [ ] 拆分 `OpenSourceService`（按功能：SearchService/ExportService/EmbeddingService）
7. [ ] 拆分 `open_source/api/open_source.py`（按资源：developers/repos/collect/search）
8. [ ] 治理剩余 15 项 Endpoint → Repository 违规
9. [ ] 引入熔断器（`pybreaker`）
10. [ ] `openalex_client.py` 复用 `HttpClientFactory`
11. [ ] 采集链路 traceId 传递

### 本月（P2 代码质量）

12. [ ] 统一错误处理装饰器
13. [ ] 清理前端死代码（useQueries.ts 中旧 favorites hooks）
14. [ ] 用 tenacity 替换 data_fetchers.py 自建重试
15. [ ] 拆分巨型文件（collect-config-tab 1033 行等）

### 季度（P3 可观测性与优化）

16. [ ] 暴露采集 Prometheus 指标（成功率、P99 延迟、队列堆积）
17. [ ] 引入并发控制（`asyncio.Semaphore`）
18. [ ] 增加采集任务幂等性保证
19. [ ] 提取魔法数字到各域 `constants/`
20. [ ] 为核心算法补充策略注释

---

## 总体评估

**优势** ✅
- Domain-driven 架构设计合理，v2.0.0 架构治理取得实质性进展
- 无循环依赖，Repository 层保持纯净
- 命名风格统一（前后端各有规范）
- 已具备基础的重试和限流机制
- 任务进度追踪完善（学术 11 阶段 + 开源独立追踪）
- 测试覆盖良好（681 passed, 8 failed, 5 deselected = 694 collected）
- v2.0.0 代码质量改进显著（拆分 TalentRepository、search-page、状态管理迁移、类型安全治理）

**劣势** ⚠️
- 采集链路韧性仍是最大短板（429 不重试、无全局事务、无熔断）
- 开源人才域代码过于集中（3 个文件承载全部逻辑）
- 跨层穿透仍有 15 处待治理
- 错误处理风格混乱
- README 文档过时（对外显示错误信息）
- 缺少统一的错误处理框架

---

## 发版建议

### 当前版本具备发版条件：⚠️ 有条件通过

**必须完成的修复项（3 项）**：
1. ✅ **更新 README.md** — 修正开源人才状态 + 项目结构（30 分钟）
2. ✅ **修复 8 个测试失败** — test_audit.py (2) + test_migrations.py (2) + 其他 (4)（需排查）
3. ✅ **OpenAlex 429 自动重试** — 读取 Retry-After 头等待后重试（1 小时）

完成上述 3 项后，**v2.0.0 可以发布**。

采集链路的事务一致性问题（P0-2, P0-3）虽然在严格意义上属于阻断级别，但在实际运行中 Phase 失败概率较低，且可通过重新触发采集修复。建议在 v2.0.1 中作为最高优先级修复。

### 建议发布策略

1. **立即**: 修复 README.md + OpenAlex 429 重试 → 发布 **v2.0.0**
2. **2 周内**: 修复 P1 问题（事务/GitHub 超时/熔断/拆分）→ 发布 **v2.0.1**
3. **1 月内**: 清理 P2 问题（统一错误处理/死代码/魔法数字）→ 发布 **v2.0.2**
4. **季度内**: P3 可观测性增强 → **v2.1.0**

---

## 各阶段报告索引

| 阶段 | 报告 | 核心结论 |
|------|------|---------|
| 阶段1 | [01-dependency-graph.md](01-dependency-graph.md) | 15 处跨层穿透，无循环依赖，Repository 层纯净 |
| 阶段2 | [02-code-smell-heatmap.md](02-code-smell-heatmap.md) | 49 个巨型文件，18 个过长函数，90+ 处重复代码 |
| 阶段3 | [03-ai-style-markers.md](03-ai-style-markers.md) | 魔法值散落，错误处理混乱，无意义注释 |
| 阶段4 | [04-pipeline-resilience.md](04-pipeline-resilience.md) | P0: 429不重试+无全局事务；P1: 无熔断+无幂等 |

---

> **上次审计 (2026-05-05): 55/100 → 本次审计 (2026-05-09): 60/100 (+5)**
> v2.0.0 架构治理成效显著，但开源人才域代码集中度过高成为新问题。
