# 智能人才库 V2.0.1 — 健康度 CT 扫描总览报告

> 扫描时间：2026-05-12
> 审计工具: health-review skill (4阶段全谱审计)

---

## 项目健康度评分: 78/100 (B+)

| 维度 | 评分 | 扣分原因 |
|------|------|---------|
| 架构合规 | 92 | 7处 Endpoint 违规 (system_config 4处, embeddings/jd_match/recommend) |
| 运行时正确性 | 95 | datetime.utcnow 已清零, TODO stub 已补全, 废弃端点已删除 |
| 静态分析 | 98 | ruff 0 error, tsc 0 error, eslint 0 error |
| 文件结构 | 65 | 1034行组件, 847行 Repository, 12个>100行函数 |
| 类型安全 | 85 | 前端 0 as any, 后端 type:ignore 待统计 |
| 设计系统 | 90 | 硬编码颜色 150+→1, semanticColors 体系完善 |
| 测试覆盖 | 60 | 689 passed 但无覆盖率报告, mock 多于真实 DB |
| 管道韧性 | 70 | GitHub A级, OpenAlex Works A级, Author/Inst D级 |
| 文档准确度 | 75 | AGENTS.md 开源状态待更新, .env.example 缺字段 |
| 依赖健康 | 80 | 待运行 npm audit / pip audit |

---

## Top 10 必须立即修复的问题

| # | 问题 | 文件 | 级别 |
|---|------|------|------|
| 1 | Author/Institution 批量获取无重试 — 一次 429 丢 25 条 | `data_fetchers.py:600-778` | **P1** |
| 2 | School Normalizer 失败记录未标记 — 永远循环重试 | `school.py:223-224` | **P1** |
| 3 | 无熔断器 — 外部 API 持续故障时无限重试 | 全局 | **P1** |
| 4 | 错误处理不一致 — 182处 HTTPException vs 2处 AppException | API 层全量 | **P1** |
| 5 | `collect-config-tab.tsx` 1034行巨型组件 | `frontend/src/pages/system-config/` | **P0** |
| 6 | `system_config.py` 4处 Endpoint 违规 | `shared/api/system_config.py` | **P1** |
| 7 | `open_source/core.py` 678行未拆分 Repository | `open_source/repositories/` | **P1** |
| 8 | 测试无覆盖率报告 — 无法量化健康度 | CI/pytest 配置 | **P1** |
| 9 | 后台采集任务无 request_id 关联 | `academic/api/collect.py` | **P1** |
| 10 | 前端 Context + Store 双轨状态管理 | `contexts/` + `stores/` | **P2** |

---

## 修复优先级时间线

### 本周 (1-2天)

1. **Author/Institution fetcher 添加 per-batch retry** — 复用 `_fetch_page_with_retry` 模式，约 30 行代码
2. **School normalizer 标记失败记录** — 添加 `batch_mark_processed(failed, "failed")` 调用，1 行
3. **pytest --cov 配置** — 在 `pyproject.toml` 添加 cov 配置并生成首次报告

### 本月 (1周内)

4. **错误处理统一** — 逐步将 `HTTPException` 迁移到 `AppException` 体系，先从 academic/api 开始
5. **collect-config-tab.tsx 拆分** — 拆为 3-4 个子组件 + 自定义 hooks
6. **system_config.py 违规修复** — 将 proxy/github 测试逻辑移入 SystemConfigTestService
7. **open_source Repository 拆分** — 按 entity 拆分 core.py (678行)

### 季度 (2-4周)

8. **熔断器引入** — tenacity 内置 or 自定义 circuit breaker 装饰器
9. **Venue 子任务游标级断点** — 记录 cursor 到 sync_venue_sub_task 表
10. **前端 Context → Zustand 统一** — 移除 AuthContext/FavoritesContext，合并到对应 Store
11. **管道专属 Prometheus 指标** — retry_count, batch_failure_rate, phase_duration

---

## 与 v2.0.0 审计对比

| 维度 | v2.0.0 | v2.0.1 | 变化 |
|------|--------|--------|------|
| Endpoint 违规 | 18 | 7 | ⬇ 61% |
| datetime.utcnow | 28文件74处 | 0 | ✅ 清零 |
| 前端硬编码颜色 | ~150+ | 1 | ⬇ 99% |
| Ant Design v5 迁移 | 13文件 bodyStyle | 0 | ✅ 清零 |
| 废弃端点 | 1 | 0 | ✅ 清零 |
| TODO 空实现 | 3处 | 0 | ✅ 清零 |
| SQLite 残留 | 7处 | 0 (仅注释清理) | ✅ 清零 |
| 测试 | 689 passed | 689 passed | — 无变化 |
| 巨型文件 | 未知 | 24个>300行, 8个>500行 | ⚠️ 新增可见度 |

---

## 详细报告索引

1. [Phase 1: 项目结构与依赖关系图](./01-dependency-graph.md)
2. [Phase 2: 代码异味热力图](./02-code-smell-heatmap.md)
3. [Phase 3: AI 生成代码特征识别](./03-ai-style-markers.md)
4. [Phase 4: 采集链路韧性分析](./04-pipeline-resilience.md)
