# 阶段2：代码异味热力图扫描 (v2.0.0 更新)

> 扫描时间：2026-05-09
> 扫描范围：`backend/app/` (~120 .py 源文件) + `frontend/src/` (~60 .ts/.tsx)
> 方法：静态行数统计 + 函数体长分析 + 重复模式搜索

---

## P0 级异味（必须立即修复）

### 1. 巨型文件（单文件 >300行）— 后端 30 个

| # | 文件路径 | 行数 | 说明 |
|---|---------|------|------|
| 1 | `domains/open_source/services/open_source_service.py` | **1398** | ⚠️ 最大文件，含搜索/导出/统计/嵌入全部逻辑 |
| 2 | `domains/open_source/repositories/open_source_repository.py` | **1002** | 全部查询集中在一个 repository |
| 3 | `domains/open_source/api/open_source.py` | **997** | 所有开源 API 端点聚合在一个文件 |
| 4 | `domains/shared/api/system_config.py` | **973** | 系统配置 + LLM/代理/嵌入连接测试 |
| 5 | `domains/shared/repositories/user_repository.py` | **847** | 用户管理全部查询 |
| 6 | `domains/academic/services/data_fetchers.py` | **785** | OpenAlex 数据采集器 |
| 7 | `domains/shared/api/permissions.py` | **767** | 权限管理 API |
| 8 | `domains/academic/repositories/raw_data_repository.py` | **702** | 原始数据仓库 |
| 9 | `domains/academic/repositories/talent/talent_search_repository.py` | **683** | 搜索仓库（v2.0 拆分后仍偏大）|
| 10 | `domains/shared/services/llm/llm_gateway.py` | **675** | LLM 网关 |
| 11 | `domains/academic/api/collect.py` | **614** | 采集任务 API |
| 12 | `domains/academic/services/collaboration_service.py` | **583** | 合作网络服务 |
| 13 | `domains/shared/services/config_service.py` | **572** | 配置服务 |
| 14 | `domains/shared/api/auth.py` | **570** | 认证 API |
| 15 | `domains/academic/api/talents.py` | **565** | 人才 API |
| 16 | `domains/academic/services/collect/orchestrator.py` | **537** | 采集编排器 |
| 17 | `domains/academic/repositories/embedding_repository.py` | **534** | 嵌入仓库 |
| 18 | `domains/academic/repositories/tech_domain_repository.py` | **533** | 技术领域仓库 |
| 19 | `domains/academic/services/sync/author_sync.py` | **502** | 作者同步服务 |
| 20 | `domains/academic/services/embedding/embedding_service.py` | **494** | 嵌入服务 |
| 21 | `domains/academic/repositories/data_version_repository.py` | **461** | 数据版本仓库 |
| 22 | `domains/academic/services/recommend/recommend_service.py` | **451** | 推荐服务 |
| 23 | `domains/open_source/schemas/open_source.py` | **441** | 开源 DTO 定义 |
| 24 | `domains/academic/services/openalex_client.py` | **421** | OpenAlex 客户端 |
| 25 | `domains/academic/services/normalizers/author.py` | **417** | 作者标准化 |
| 26 | `domains/open_source/services/github_client.py` | **412** | GitHub 客户端 |
| 27 | `domains/open_source/services/collectors/github_collector.py` | **411** | GitHub 采集器 |
| 28 | `domains/academic/api/tech_domain.py` | **396** | 技术领域 API |
| 29 | `domains/academic/repositories/talent/base_talent_repository.py` | **393** | 基础人才仓库（v2.0 拆分后）|
| 30 | `domains/academic/services/jd_match/jd_match_service.py` | **384** | JD 匹配服务 |

> 后端共 **30** 个文件超过 300 行，占比约 **25%**。
> **v2.0.0 改进**: TalentRepository 从 1188 行拆分为 3 个文件，但 OpenSourceService 成为新的最大文件 (1398行)。

### 巨型文件 — 前端 19 个

| # | 文件路径 | 行数 | 说明 |
|---|---------|------|------|
| 1 | `pages/system-config/components/collect-config-tab.tsx` | **1033** | 采集配置标签（v2.0 反而增长）|
| 2 | `pages/user/favorites-page.tsx` | **706** | 收藏页面 |
| 3 | `pages/admin/admin-page.tsx` | **585** | 管理页面 |
| 4 | `types/index.ts` | **546** | 所有类型定义集中在一个文件 |
| 5 | `pages/academic/components/search-tab.tsx` | **544** | 搜索子标签（v2.0 拆分后仍偏大）|
| 6 | `pages/admin/data-version-page.tsx` | **543** | 数据版本页面 |
| 7 | `pages/academic/academic-talent-detail-page.tsx` | **526** | 人才详情页 |
| 8 | `hooks/useQueries.ts` | **481** | Query Hooks |
| 9 | `pages/open-source/repo-detail-page.tsx` | **473** | 仓库详情页 |
| 10 | `pages/system-config/components/os-repo-config-sub-tab.tsx` | **469** | 仓库配置子标签 |
| 11 | `pages/open-source/open-source-page.tsx` | **468** | 开源首页 |
| 12 | `pages/academic/academic-home-page.tsx` | **416** | 学术首页 |
| 13 | `pages/academic/academic-country-school-page.tsx` | **412** | 国家学校页面 |
| 14 | `pages/open-source/open-source-developer-detail-page.tsx` | **408** | 开发者详情 |
| 15 | `pages/open-source/open-source-search-page.tsx` | **393** | 开源搜索 |
| 16 | `pages/industry/industry-demo-page.tsx` | **386** | 行业演示页 |
| 17 | `pages/academic/academic-tech-domain-page.tsx` | **373** | 技术领域页面 |
| 18 | `pages/academic/academic-school-detail-page.tsx` | **336** | 学校详情页 |
| 19 | `pages/competition/competition-demo-page.tsx` | **329** | 竞赛演示页 |

> 前端共 **19** 个文件超过 300 行，占比约 **32%**。
> **v2.0.0 改进**: `academic-search-page.tsx` 从 1141 行拆分为 3 个 tab 组件，但 collect-config-tab 增长至 1033 行。

---

### 2. 过长函数（单函数体 >100行）

#### 后端

| # | 文件路径 | 函数名 | 体长 | 说明 |
|---|---------|--------|------|------|
| 1 | `academic/repositories/embedding_repository.py` | `_is_postgres` | ~500 | 巨大的条件判断函数 |
| 2 | `academic/services/data_fetchers.py` | `with_retry` | ~400 | 重试装饰器 |
| 3 | `academic/services/data_fetchers.py` | `extract_institutions` | ~300 | 机构数据提取 |
| 4 | `open_source/services/open_source_service.py` | 多个方法 | 100-200 | Service 方法过长 |
| 5 | `shared/api/system_config.py` | `test_proxy_connection` | ~230 | 代理连接测试 |
| 6 | `shared/api/system_config.py` | `_test_embedding_model` | ~140 | 嵌入模型测试 |
| 7 | `shared/api/auth.py` | `login` | ~130 | 登录逻辑 |
| 8 | `open_source/api/open_source.py` | 多个端点函数 | 100-150 | 端点函数逻辑过重 |
| 9 | `shared/api/system_config.py` | `_test_chat_model` | ~110 | 聊天模型测试 |
| 10 | `academic/api/talents.py` | `export_talents` | ~100 | 人才导出 |

#### 前端

| # | 文件路径 | 组件名 | 体长 | 说明 |
|---|---------|--------|------|------|
| 1 | `pages/system-config/components/collect-config-tab.tsx` | `CollectConfigTab` | ~970 | 配置标签组件 |
| 2 | `pages/user/favorites-page.tsx` | `FavoritesPage` | ~660 | 收藏页面 |
| 3 | `pages/academic/components/search-tab.tsx` | `SearchTab` | ~500 | 搜索标签（v2.0 拆分后）|
| 4 | `pages/admin/admin-page.tsx` | `AdminPage` | ~500 | 管理页面 |
| 5 | `pages/admin/data-version-page.tsx` | `DataVersionPage` | ~450 | 数据版本页面 |
| 6 | `pages/academic/academic-talent-detail-page.tsx` | `TalentDetailPage` | ~420 | 人才详情 |
| 7 | `pages/open-source/repo-detail-page.tsx` | `RepoDetailPage` | ~430 | 仓库详情 |
| 8 | `pages/open-source/open-source-developer-detail-page.tsx` | `DeveloperDetailPage` | ~370 | 开发者详情 |

---

### 3. 圈复杂度估算（>15）

| # | 文件路径 | 函数名 | 估算圈复杂度 | 依据 |
|---|---------|--------|-------------|------|
| 1 | `open_source/services/open_source_service.py` | `search_developers` | ~22 | 多过滤条件 + 排序 + 分页 |
| 2 | `academic/services/data_fetchers.py` | `with_retry` | ~20 | 多重装饰器 + 异常分支 |
| 3 | `shared/api/system_config.py` | `test_proxy_connection` | ~18 | 多协议测试分支 |
| 4 | `shared/services/llm/llm_gateway.py` | `call_llm` | ~16 | 多 Provider 路由 + 重试 |
| 5 | `academic/services/search/search_service.py` | `search` | ~16 | 多策略路由 + 降级逻辑 |

---

## P1 级异味（建议本月修复）

### 4. 重复代码（60+ 处）

**后端通用异常处理模式**（散落于 20+ 个文件）：
```python
except Exception as e:
    logger.error(f"...failed: {e}")
```

| 高频位置 | 出现次数 |
|---------|---------|
| `shared/api/system_config.py` | 5 处测试错误处理 |
| `open_source/api/open_source.py` | 4 处采集错误处理 |
| `academic/api/*.py` | 各 1-2 处 |
| `academic/services/data_fetchers.py` | 3 处数据解析错误处理 |

**前端 API 调用模式**（30+ 处重复）：
```typescript
try { setLoading(true); const res = await api.xxx.yyy(); setData(res.data); }
catch (err) { message.error('...'); }
finally { setLoading(false); }
```

**前端 Loading/Empty 状态渲染**（几乎所有列表页重复）：
```tsx
{loading ? <Spin /> : data.length === 0 ? <Empty /> : <Table ... />}
```

### 5. 命名风格

| 域 | 风格 | 评估 |
|----|------|------|
| 后端 | snake_case (函数/变量) + PascalCase (类/Schema) + UPPER_SNAKE (常量) | ✅ 统一 |
| 前端 | camelCase (变量/函数) + PascalCase (类型/组件) + snake_case (API DTO字段) | ✅ 有意识分层 |

> 无命名混乱问题。

---

## P2 级异味（季度优化）

### 6. 前端死代码

| # | 文件路径 | 名称 | 说明 |
|---|---------|------|------|
| 1 | `hooks/useQueries.ts` | `useTalentWorks` | 未被任何页面 import |
| 2 | `hooks/useQueries.ts` | `useTalentCollaborations` | 未被任何页面 import |
| 3 | `hooks/useQueries.ts` | `useSchoolTalents` | 未被任何页面 import |
| 4 | `hooks/useQueries.ts` | `useFavoriteIds` | 未被任何页面 import (已迁移到 Zustand) |
| 5 | `hooks/useQueries.ts` | `useFavoriteCheck` | 未被任何页面 import |
| 6 | `hooks/useQueries.ts` | `useAddFavorite` | 未被任何页面 import |
| 7 | `hooks/useQueries.ts` | `useRemoveFavorite` | 未被任何页面 import |
| 8 | `hooks/useQueries.ts` | `useCollectTechDomains` | 未被任何页面 import |
| 9 | `hooks/useQueries.ts` | `useCollectTasks` | 未被任何页面 import |
| 10 | `hooks/useQueries.ts` | `useActiveCollectTasks` | 未被任何页面 import |
| 11 | `constants/roleType.ts` | `getRoleTypeColor`, `isValidRoleType`, `getRoleTypeOptions` | 未被引用 |
| 12 | `services/api.ts` | `createCancellableRequest`, `isCancellationError` | 无实际 import |

> `useQueries.ts` 中 v2.0 将 favorites 迁移至 Zustand 后，旧的 favorites hooks 变成死代码。

### 7. 后端架构问题

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| 1 | `open_source/api/open_source.py` 单文件 997 行 | 整个文件 | 应拆分为 developers/repos/collect/search/export/embedding 子模块 |
| 2 | `open_source/services/open_source_service.py` 单文件 1398 行 | 整个文件 | 应按功能拆分（search/export/embedding/crud） |
| 3 | `open_source/repositories/open_source_repository.py` 1002 行 | 整个文件 | 应按实体拆分（developer/repo/contribution/collect） |
| 4 | `shared/api/system_config.py` 973 行 | 整个文件 | 连接测试逻辑应移至 Service 层 |

---

## 异味统计总览

| 异味类型 | P0 | P1 | P2 | 总计 |
|---------|----|----|----|------|
| 巨型文件 (>300行) | 49 | — | — | 49 |
| 过长函数 (>100行) | 18 | — | — | 18 |
| 高圈复杂度 (>15) | 5 | — | — | 5 |
| 重复代码 | — | 90+ | — | 90+ |
| 命名混乱 | — | 0 | — | 0 |
| 死代码 | — | — | 12 | 12 |

### v2.0.0 改进项目

| 项目 | 变更前 | 变更后 | 状态 |
|------|--------|--------|------|
| TalentRepository | 1157 行 | 拆分为 base(393) + search(683) + export | ✅ |
| academic-search-page | 1166 行 | 拆分为 SearchTab + JDMatchTab + RecommendTab | ✅ |
| 前端 any 类型 | 21 处 | 治理为 unknown + 类型守卫 | ✅ |
| AuthContext/FavoritesContext | Context API | 迁移至 Zustand | ✅ |
| search.py/collect.py/embeddings.py | 13 项跨层穿透 | 已治理 | ✅ |
| CI | 仅后端测试 | 新增前端 Vitest | ✅ |

---

> 关联报告：[01-dependency-graph.md](01-dependency-graph.md) | [03-ai-style-markers.md](03-ai-style-markers.md) | [04-pipeline-resilience.md](04-pipeline-resilience.md)
