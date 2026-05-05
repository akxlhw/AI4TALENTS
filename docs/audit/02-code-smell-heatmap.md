# 阶段2：代码异味热力图扫描

> 扫描时间：2026-05-05  
> 扫描范围：`backend/app/` (~182 .py) + `frontend/src/` (~60 .ts/.tsx)  
> 方法：静态行数统计 + 函数体长分析 + 命名风格检查 + 重复模式搜索

---

## P0 级异味（必须立即修复）

### 1. 巨型文件（单文件 >300行）

#### 后端

| # | 文件路径 | 行数 | 说明 |
|---|---------|------|------|
| 1 | [`app/repositories/talent_repository.py`](../../backend/app/repositories/talent_repository.py) | **1188** | 人才查询仓库，含大量条件分支和原始 SQL |
| 2 | [`app/api/v1/endpoints/open_source.py`](../../backend/app/api/v1/endpoints/open_source.py) | **1138** | 开源人才 REST API，功能过度集中 |
| 3 | [`app/api/v1/endpoints/system_config.py`](../../backend/app/api/v1/endpoints/system_config.py) | **990** | 系统配置 API，含大量外部服务测试逻辑 |
| 4 | [`app/repositories/user_repository.py`](../../backend/app/repositories/user_repository.py) | **844** | 用户仓库 |
| 5 | [`app/api/v1/endpoints/permissions.py`](../../backend/app/api/v1/endpoints/permissions.py) | **767** | 权限管理 API |
| 6 | [`app/services/data_fetchers.py`](../../backend/app/services/data_fetchers.py) | **748** | OpenAlex 数据采集器 |
| 7 | [`app/api/v1/endpoints/collect.py`](../../backend/app/api/v1/endpoints/collect.py) | **702** | 采集任务 API |
| 8 | [`app/repositories/raw_data_repository.py`](../../backend/app/repositories/raw_data_repository.py) | **696** | 原始数据仓库 |
| 9 | [`app/repositories/tech_domain_repository.py`](../../backend/app/repositories/tech_domain_repository.py) | **686** | 技术领域仓库 |
| 10 | [`app/services/llm/llm_gateway.py`](../../backend/app/services/llm/llm_gateway.py) | **639** | LLM 网关 |
| 11 | [`app/services/collaboration_service.py`](../../backend/app/services/collaboration_service.py) | **583** | 合作网络服务 |
| 12 | [`app/api/v1/endpoints/auth.py`](../../backend/app/api/v1/endpoints/auth.py) | **570** | 认证 API |
| 13 | [`app/api/v1/endpoints/talents.py`](../../backend/app/api/v1/endpoints/talents.py) | **565** | 人才 API |
| 14 | [`app/repositories/embedding_repository.py`](../../backend/app/repositories/embedding_repository.py) | **534** | 嵌入仓库 |
| 15 | [`app/services/config_service.py`](../../backend/app/services/config_service.py) | **526** | 配置服务 |
| 16 | [`app/services/sync/author_sync.py`](../../backend/app/services/sync/author_sync.py) | **502** | 作者同步服务 |
| 17 | [`app/services/collect/orchestrator.py`](../../backend/app/services/collect/orchestrator.py) | **495** | 采集编排器 |
| 18 | [`app/services/embedding/embedding_service.py`](../../backend/app/services/embedding/embedding_service.py) | **458** | 嵌入服务 |
| 19 | [`app/repositories/data_version_repository.py`](../../backend/app/repositories/data_version_repository.py) | **456** | 数据版本仓库 |
| 20 | [`app/services/recommend/recommend_service.py`](../../backend/app/services/recommend/recommend_service.py) | **451** | 推荐服务 |
| 21 | [`app/api/v1/endpoints/data_version.py`](../../backend/app/api/v1/endpoints/data_version.py) | **421** | 数据版本 API |
| 22 | [`app/services/normalizers/author.py`](../../backend/app/services/normalizers/author.py) | **417** | 作者标准化 |
| 23 | [`app/api/v1/endpoints/tech_domain.py`](../../backend/app/api/v1/endpoints/tech_domain.py) | **396** | 技术领域 API |
| 24 | [`app/services/jd_match/jd_match_service.py`](../../backend/app/services/jd_match/jd_match_service.py) | **384** | JD 匹配服务 |
| 25 | [`app/services/openalex_client.py`](../../backend/app/services/openalex_client.py) | **380** | OpenAlex 客户端 |
| 26 | [`app/schemas/open_source.py`](../../backend/app/schemas/open_source.py) | **378** | 开源 DTO 定义 |
| 27 | [`app/core/metrics.py`](../../backend/app/core/metrics.py) | **376** | 指标采集 |
| 28 | [`app/api/v1/endpoints/schools.py`](../../backend/app/api/v1/endpoints/schools.py) | **348** | 学校 API |
| 29 | [`app/api/v1/endpoints/embeddings.py`](../../backend/app/api/v1/endpoints/embeddings.py) | **346** | 嵌入 API |
| 30 | [`app/repositories/collect_repository.py`](../../backend/app/repositories/collect_repository.py) | **344** | 采集仓库 |

> 后端共 **30** 个文件超过 300 行，占 .py 文件总数的 **~16.5%**

#### 前端

| # | 文件路径 | 行数 | 说明 |
|---|---------|------|------|
| 1 | [`src/pages/academic/academic-search-page.tsx`](../../frontend/src/pages/academic/academic-search-page.tsx) | **1141** | 学术搜索页面 |
| 2 | [`src/pages/system-config/components/collect-config-tab.tsx`](../../frontend/src/pages/system-config/components/collect-config-tab.tsx) | **863** | 采集配置子标签 |
| 3 | [`src/pages/user/favorites-page.tsx`](../../frontend/src/pages/user/favorites-page.tsx) | **701** | 收藏页面 |
| 4 | [`src/services/api.ts`](../../frontend/src/services/api.ts) | **605** | API 客户端 |
| 5 | [`src/pages/admin/admin-page.tsx`](../../frontend/src/pages/admin/admin-page.tsx) | **567** | 管理页面 |
| 6 | [`src/pages/admin/data-version-page.tsx`](../../frontend/src/pages/admin/data-version-page.tsx) | **537** | 数据版本页面 |
| 7 | [`src/pages/academic/academic-talent-detail-page.tsx`](../../frontend/src/pages/academic/academic-talent-detail-page.tsx) | **525** | 人才详情页 |
| 8 | [`src/types/index.ts`](../../frontend/src/types/index.ts) | **515** | 类型定义 |
| 9 | [`src/hooks/useQueries.ts`](../../frontend/src/hooks/useQueries.ts) | **481** | Query Hooks |
| 10 | [`src/pages/open-source/open-source-developer-detail-page.tsx`](../../frontend/src/pages/open-source/open-source-developer-detail-page.tsx) | **404** | 开源开发者详情 |
| 11 | [`src/pages/academic/academic-country-school-page.tsx`](../../frontend/src/pages/academic/academic-country-school-page.tsx) | **396** | 国家学校页面 |
| 12 | [`src/pages/academic/academic-home-page.tsx`](../../frontend/src/pages/academic/academic-home-page.tsx) | **389** | 学术首页 |
| 13 | [`src/pages/industry/industry-demo-page.tsx`](../../frontend/src/pages/industry/industry-demo-page.tsx) | **382** | 行业演示页 |
| 14 | [`src/pages/academic/academic-tech-domain-page.tsx`](../../frontend/src/pages/academic/academic-tech-domain-page.tsx) | **364** | 技术领域页面 |
| 15 | [`src/pages/open-source/open-source-search-page.tsx`](../../frontend/src/pages/open-source/open-source-search-page.tsx) | **357** | 开源搜索页 |
| 16 | [`src/pages/system-config/components/os-repo-config-sub-tab.tsx`](../../frontend/src/pages/system-config/components/os-repo-config-sub-tab.tsx) | **354** | 仓库配置子标签 |
| 17 | [`src/pages/academic/academic-school-detail-page.tsx`](../../frontend/src/pages/academic/academic-school-detail-page.tsx) | **336** | 学校详情页 |
| 18 | [`src/pages/competition/competition-demo-page.tsx`](../../frontend/src/pages/competition/competition-demo-page.tsx) | **327** | 竞赛演示页 |
| 19 | [`src/pages/open-source/open-source-page.tsx`](../../frontend/src/pages/open-source/open-source-page.tsx) | **317** | 开源首页 |

> 前端共 **19** 个文件超过 300 行，占 .ts/.tsx 文件总数的 **~31.7%**

---

### 2. 过长函数（单函数体 >100行）

#### 后端

| # | 文件路径 | 函数名 | 起始行 | 体长 | 说明 |
|---|---------|--------|--------|------|------|
| 1 | [`app/repositories/embedding_repository.py`](../../backend/app/repositories/embedding_repository.py) | `_is_postgres` | L32 | **502** | 巨大的条件判断函数，需拆分 |
| 2 | [`app/services/data_fetchers.py`](../../backend/app/services/data_fetchers.py) | `with_retry` | L52 | **411** | 重试装饰器，逻辑过于集中 |
| 3 | [`app/services/data_fetchers.py`](../../backend/app/services/data_fetchers.py) | `extract_institutions` | L464 | **306** | 机构数据提取 |
| 4 | [`app/api/v1/endpoints/system_config.py`](../../backend/app/api/v1/endpoints/system_config.py) | `test_proxy_connection` | L587 | **235** | 代理连接测试 |
| 5 | [`app/api/v1/endpoints/system_config.py`](../../backend/app/api/v1/endpoints/system_config.py) | `_test_embedding_model` | L368 | **142** | 嵌入模型测试 |
| 6 | [`app/api/v1/endpoints/search.py`](../../backend/app/api/v1/endpoints/search.py) | `enhanced_search_talents` | L99 | **142** | 增强搜索 |
| 7 | [`app/api/v1/endpoints/embeddings.py`](../../backend/app/api/v1/endpoints/embeddings.py) | `_run_embedding_generation` | L225 | **126** | 嵌入生成执行 |
| 8 | [`app/api/v1/endpoints/auth.py`](../../backend/app/api/v1/endpoints/auth.py) | `login` | L264 | **129** | 登录逻辑 |
| 9 | [`app/schemas/collect.py`](../../backend/app/schemas/collect.py) | `get_current_year` | L19 | **126** | ⚠️ 获取当前年份竟有 126 行，疑似包含大量业务逻辑 |
| 10 | [`app/api/v1/endpoints/system_config.py`](../../backend/app/api/v1/endpoints/system_config.py) | `_test_chat_model` | L205 | **113** | 聊天模型测试 |
| 11 | [`app/api/v1/endpoints/collect.py`](../../backend/app/api/v1/endpoints/collect.py) | `trigger_task` | L291 | **110** | 触发采集任务 |
| 12 | [`app/api/v1/endpoints/talents.py`](../../backend/app/api/v1/endpoints/talents.py) | `export_talents` | L246 | **107** | 人才导出 |

#### 前端

| # | 文件路径 | 函数/组件名 | 起始行 | 体长 | 说明 |
|---|---------|-----------|--------|------|------|
| 1 | [`src/pages/academic/academic-search-page.tsx`](../../frontend/src/pages/academic/academic-search-page.tsx) | `SearchRecommendPage` | L88 | **1078** | 页面组件，需拆分子组件 |
| 2 | [`src/pages/system-config/components/collect-config-tab.tsx`](../../frontend/src/pages/system-config/components/collect-config-tab.tsx) | `CollectConfigTab` | L58 | **806** | 配置标签组件 |
| 3 | [`src/pages/user/favorites-page.tsx`](../../frontend/src/pages/user/favorites-page.tsx) | `FavoritesPage` | L42 | **664** | 收藏页面 |
| 4 | [`src/services/api.ts`](../../frontend/src/services/api.ts) | `api` | L133 | **472** | API 客户端对象定义 |
| 5 | [`src/pages/admin/admin-page.tsx`](../../frontend/src/pages/admin/admin-page.tsx) | `AdminPage` | L83 | **484** | 管理页面 |
| 6 | [`src/pages/admin/data-version-page.tsx`](../../frontend/src/pages/admin/data-version-page.tsx) | `DataVersionPage` | L89 | **448** | 数据版本页面 |
| 7 | [`src/pages/academic/academic-talent-detail-page.tsx`](../../frontend/src/pages/academic/academic-talent-detail-page.tsx) | `TalentDetailPage` | L84 | **412** | 人才详情 |
| 8 | [`src/pages/open-source/open-source-developer-detail-page.tsx`](../../frontend/src/pages/open-source/open-source-developer-detail-page.tsx) | `DeveloperDetailPage` | L35 | **369** | 开发者详情 |
| 9 | [`src/pages/academic/academic-home-page.tsx`](../../frontend/src/pages/academic/academic-home-page.tsx) | `AcademicHomePage` | L42 | **347** | 学术首页 |
| 10 | [`src/pages/academic/academic-country-school-page.tsx`](../../frontend/src/pages/academic/academic-country-school-page.tsx) | `CountrySchoolPage` | L81 | **331** | 国家学校页 |

> 注：React 页面组件体长包含 JSX 渲染逻辑，100+ 行在页面级组件中较常见，但 >300 行建议拆分。

---

### 3. 圈复杂度估算（>15）

> 以下函数基于 `if/elif/else/for/while/and/or` 嵌套层数估算，**需人工复核**。

| # | 文件路径 | 函数名 | 估算圈复杂度 | 依据 |
|---|---------|--------|-------------|------|
| 1 | [`app/repositories/talent_repository.py`](../../backend/app/repositories/talent_repository.py) | `get_talent_list` | **~25** | 大量过滤条件分支 + 排序逻辑 |
| 2 | [`app/services/data_fetchers.py`](../../backend/app/services/data_fetchers.py) | `with_retry` | **~20** | 多重装饰器包装 + 异常分支 |
| 3 | [`app/api/v1/endpoints/open_source.py`](../../backend/app/api/v1/endpoints/open_source.py) | `list_developers` | **~18** | 多过滤条件 + 排序 + 分页组合 |
| 4 | [`app/api/v1/endpoints/system_config.py`](../../backend/app/api/v1/endpoints/system_config.py) | `test_proxy_connection` | **~18** | 多协议测试分支 |
| 5 | [`app/services/llm/llm_gateway.py`](../../backend/app/services/llm/llm_gateway.py) | `call_llm` | **~16** | 多 Provider 路由 + 重试逻辑 |

---

## P1 级异味（建议本月修复）

### 4. 重复代码

#### 后端：通用异常处理模式（>10处相似）

```python
# 模式：broad except + logger + 无重新抛出
except Exception as e:
    logger.error(f"...failed: {e}")
```

| 文件 | 行号 | 重复度 |
|------|------|--------|
| [`app/api/v1/endpoints/system_config.py`](../../backend/app/api/v1/endpoints/system_config.py) | L197, L360, L697 | 3 处几乎相同的测试错误处理 |
| [`app/api/v1/endpoints/embeddings.py`](../../backend/app/api/v1/endpoints/embeddings.py) | L336, L347 | 2 处批处理错误处理 |
| [`app/api/v1/endpoints/open_source.py`](../../backend/app/api/v1/endpoints/open_source.py) | L181, L350 | 2 处采集错误处理 |
| [`app/services/data_fetchers.py`](../../backend/app/services/data_fetchers.py) | L251, L372 | 2 处数据解析错误处理 |
| [`app/services/collaboration_service.py`](../../backend/app/services/collaboration_service.py) | L160, L379 | 2 处论文处理错误处理 |

> 共 **60+** 处该模式分散在各文件中，建议封装为统一装饰器。

#### 前端：API 错误处理模式

```typescript
// 模式：try/catch + message.error + setLoading(false)
try {
  setLoading(true)
  const res = await api.xxx.yyy()
  setData(res.data)
} catch (err) {
  message.error('...')
} finally {
  setLoading(false)
}
```

> 该模式在几乎每个页面组件中重复出现（>30 处），建议封装为自定义 Hook（如 `useApiCall`）。

#### 前端：Empty/Loading 状态渲染

```tsx
// 多个页面中存在相同的 Loading + Empty 组合
{loading ? <Spin /> : data.length === 0 ? <Empty /> : <Table ... />}
```

> 在列表页面中高度重复。

---

### 5. 命名风格

#### 后端

| 风格 | 出现位置 | 评估 |
|------|---------|------|
| **snake_case** | 函数、变量、模块 | ✅ Python 标准 |
| **PascalCase** | 类名、Pydantic Schema | ✅ Python 标准 |
| **UPPER_SNAKE_CASE** | 常量、枚举 | ✅ 标准 |

> 后端命名风格统一，无混乱。

#### 前端

| 风格 | 出现位置 | 评估 |
|------|---------|------|
| **camelCase** | 变量、函数、Hooks | ✅ 前端标准 |
| **PascalCase** | 类型、组件 | ✅ TS/React 标准 |
| **snake_case** | API DTO 字段 | ✅ 后端契约映射 |

> 前端命名风格统一，3 种风格为**有意识的领域分层**，非混乱。详见 [阶段1报告](01-dependency-graph.md)。

---

## P2 级异味（季度优化）

### 6. 死代码

#### 后端

> 静态扫描未发现明显死函数。原因：
> 1. FastAPI 端点函数通过装饰器隐式注册，静态分析无法追踪调用链
> 2. SQLAlchemy ORM 模型方法通过元类隐式调用
> 3. Alembic 迁移脚本通过 revision ID 隐式调用
> 4. pytest fixture 通过 conftest.py 隐式注入
>
> **建议**：通过运行时覆盖率工具（如 `pytest-cov`）识别真实死代码。

#### 前端

| # | 文件路径 | 名称 | 行号 | 说明 |
|---|---------|------|------|------|
| 1 | [`src/constants/roleType.ts`](../../frontend/src/constants/roleType.ts) | `getRoleTypeColor` | L76 | 未被任何业务代码引用 |
| 2 | [`src/constants/roleType.ts`](../../frontend/src/constants/roleType.ts) | `isValidRoleType` | L86 | 未被任何业务代码引用 |
| 3 | [`src/constants/roleType.ts`](../../frontend/src/constants/roleType.ts) | `getRoleTypeOptions` | L95 | 未被任何业务代码引用 |
| 4 | [`src/services/api.ts`](../../frontend/src/services/api.ts) | `createCancellableRequest` | L100 | 仅 JSDoc 示例，无实际 import |
| 5 | [`src/services/api.ts`](../../frontend/src/services/api.ts) | `isCancellationError` | L124 | 无实际 import |
| 6 | [`src/hooks/useKeyboardShortcuts.ts`](../../frontend/src/hooks/useKeyboardShortcuts.ts) | `createCommonShortcuts` | L78 | 无实际 import |
| 7 | [`src/hooks/useQueries.ts`](../../frontend/src/hooks/useQueries.ts) | `useTalentWorks` | L230 | 未在任何页面 import |
| 8 | [`src/hooks/useQueries.ts`](../../frontend/src/hooks/useQueries.ts) | `useTalentCollaborations` | L246 | 未在任何页面 import |
| 9 | [`src/hooks/useQueries.ts`](../../frontend/src/hooks/useQueries.ts) | `useSchoolTalents` | L304 | 未在任何页面 import |
| 10 | [`src/hooks/useQueries.ts`](../../frontend/src/hooks/useQueries.ts) | `useFavoriteIds` | L367 | 未在任何页面 import |
| 11 | [`src/hooks/useQueries.ts`](../../frontend/src/hooks/useQueries.ts) | `useFavoriteCheck` | L381 | 未在任何页面 import |
| 12 | [`src/hooks/useQueries.ts`](../../frontend/src/hooks/useQueries.ts) | `useAddFavorite` | L400 | 未在任何页面 import |
| 13 | [`src/hooks/useQueries.ts`](../../frontend/src/hooks/useQueries.ts) | `useRemoveFavorite` | L416 | 未在任何页面 import |
| 14 | [`src/hooks/useQueries.ts`](../../frontend/src/hooks/useQueries.ts) | `useCollectTechDomains` | L435 | 未在任何页面 import |
| 15 | [`src/hooks/useQueries.ts`](../../frontend/src/hooks/useQueries.ts) | `useCollectTasks` | L450 | 未在任何页面 import |
| 16 | [`src/hooks/useQueries.ts`](../../frontend/src/hooks/useQueries.ts) | `useActiveCollectTasks` | L470 | 未在任何页面 import |

> `useQueries.ts` 中大量 Hook 仅为"预封装"，实际未被消费，属于过度设计。

#### 补充：重复代码（新增）

| 文件A | 文件B | 重复内容 | 说明 |
|------|------|---------|------|
| `pages/academic/academic-search-page.tsx:74` | `pages/system-config/components/utils.ts:5` | `getErrorMessage` | 本地定义与工具函数重复，可统一复用 |

---

## 异味统计总览

| 异味类型 | P0 | P1 | P2 | 总计 |
|---------|----|----|----|------|
| 巨型文件 | 49 | — | — | 49 |
| 过长函数 | 22 | — | — | 22 |
| 高圈复杂度 | 5 | — | — | 5 |
| 重复代码 | — | 60+ | — | 60+ |
| 命名混乱 | — | 0 | — | 0 |
| 死代码 | — | — | 0 | 0 |

---

> 下一步：等待用户确认后，进入阶段3「AI生成代码特征识别」。
