# Phase 2: 代码异味热力图 (全面审计)

> 审计时间：2026-05-15

## P0 级: 巨型文件 (>300行)

### 后端 Top 15 (>300行共 42 个文件)

| 行数 | 文件 | 说明 |
|------|------|------|
| 847 | `shared/repositories/user_repository.py` | 用户仓储，含大量查询 |
| 808 | `academic/services/data_fetchers.py` | OpenAlex 数据获取器 |
| 777 | `shared/api/permissions.py` | 权限管理 API |
| 702 | `academic/repositories/raw_data_repository.py` | 原始数据仓储 |
| 683 | `academic/repositories/talent/talent_search_repository.py` | 人才搜索仓储 |
| 678 | `open_source/repositories/open_source/core.py` | 开源核心仓储 |
| 599 | `academic/api/collect.py` | 采集 API |
| 597 | `shared/api/auth.py` | 认证 API |
| 596 | `shared/services/config_service.py` | 配置服务 |
| 583 | `academic/services/collaboration_service.py` | 合作关系服务 |
| 562 | `academic/api/talents.py` | 人才 API |
| 537 | `academic/services/collect/orchestrator.py` | 采集编排器 |
| 535 | `academic/repositories/embedding_repository.py` | 嵌入仓储 |
| 533 | `academic/repositories/tech_domain_repository.py` | 技术领域仓储 |
| 508 | `shared/services/system_config_test_service.py` | 系统配置测试服务 |

> >500行: 8个文件; >300行: 42个文件

### 前端 Top 7 (>300行共 19 个文件)

| 行数 | 文件 | 说明 |
|------|------|------|
| 1034 | `system-config/components/collect-config-tab.tsx` | **最大文件** — 采集配置页 |
| 707 | `user/favorites-page.tsx` | 收藏页面 |
| 585 | `admin/admin-page.tsx` | 管理后台 |
| 545 | `types/index.ts` | 统一类型定义 |
| 544 | `admin/data-version-page.tsx` | 数据版本页 |
| 543 | `pages/academic/components/search-tab.tsx` | 搜索标签页 |
| 531 | `pages/academic/academic-talent-detail-page.tsx` | 人才详情页 |

---

## P0 级: 复杂函数 (圈复杂度 >15)

| 分支数 | 函数 | 文件 | 行范围 |
|--------|------|------|--------|
| ~41 | `_test_proxy_connection` | `shared/services/system_config_test_service.py` | 268-435 |
| ~36 | `_bulk_upsert_postgres` | `academic/services/sync/author_sync.py` | 312-502 |
| ~33 | `_find_similar_by_tags` | `academic/services/recommend/recommend_service.py` | 309-448 |
| ~33 | `_process_contributor` | `open_source/services/collectors/github_collector.py` | 178-332 |
| ~28 | `_generate_embedding_batch_minimax` | `shared/services/llm/llm_embedding_mixin.py` | 207-372 |
| ~27 | `search` (hybrid) | `academic/services/search/strategies/hybrid.py` | 25-180 |
| ~22 | `compute_selected_works_for_all_authors` | `academic/services/data_fetchers.py` | 393-477 |
| ~22 | `normalize_all_authors` | `academic/services/normalizers/author.py` | 313-417 |
| ~21 | `get_collaboration_network` | `academic/services/collaboration_service.py` | 385-494 |
| ~21 | `_semantic_or_hybrid_search` | `open_source/services/os_developer_service.py` | 281-381 |
| ~19 | `get_talent_list_by_cursor` | `academic/repositories/tech_domain_repository.py` | 270-402 |
| ~19 | `parse_jd` | `shared/services/llm/llm_gateway.py` | 162-275 |
| ~18 | `execute_task` | `academic/services/collect/orchestrator.py` | 129-267 |

> 共 24 个函数圈复杂度 >15

---

## P1 级: 命名不一致

### favourite / favorite 拼写混用

同一 open_source 域内混用英式和美式拼写:

| 文件 | "favourite" | "favorite" |
|------|------------|------------|
| `open_source/api/favourites.py` | 18 | 25 |
| `open_source/models/open_source.py` | 3 | 1 |
| `open_source/services/os_favourite_service.py` | 30 | 1 |
| `open_source/schemas/open_source.py` | 1 | 9 |

导致 API 路由 `POST /favourites` 但响应模型 `OSFavoriteResponse`。

---

## P1 级: 重复代码

| 模式 | 位置 | 说明 |
|------|------|------|
| 纯委托门面 | `open_source_service.py` (302行, 47方法) | 100% 方法透传，零业务逻辑 |
| 嵌入服务分裂 | `os_embedding_service.py` + `open_source_embedding_service.py` | 学术域为单一文件，开源域拆两个 |
| 向量搜索重复 | `academic/.../talent_search_repository.py` vs `open_source/.../advanced.py` | 几乎相同的 pgvector 查询 (~110行) |
| 收藏 CRUD 重复 | `academic/api/favorites.py` vs `open_source/api/favourites.py` | 相同 CRUD 结构未抽象 |
| 后台嵌入生成 | 两域各自实现相同批量循环+取消检查+进度更新 | docstring: "Follows same pattern as academic" |
| `_and_commit` 重复 | `user_repository.py` (11对方法) | 每对仅多一行 `session.commit()` |

---

## P1 级: 过长函数 (>100行)

TOP 10:

| 行数 | 函数 | 文件 |
|------|------|------|
| 191 | `_bulk_upsert_postgres` | `academic/services/sync/author_sync.py` |
| 168 | `_test_proxy_connection` | `shared/services/system_config_test_service.py` |
| 166 | `_generate_embedding_batch_minimax` | `shared/services/llm/llm_embedding_mixin.py` |
| 156 | `search` (hybrid) | `academic/services/search/strategies/hybrid.py` |
| 155 | `_process_contributor` | `open_source/services/collectors/github_collector.py` |
| 140 | `_find_similar_by_tags` | `academic/services/recommend/recommend_service.py` |
| 139 | `execute_task` | `academic/services/collect/orchestrator.py` |
| 133 | `get_talent_list_by_cursor` | `academic/repositories/tech_domain_repository.py` |
| 132 | `_test_embedding_model` | `shared/services/system_config_test_service.py` |
| 130 | `get_talent_list` | `academic/repositories/tech_domain_repository.py` |

> 共 21 个函数 >100行

---

## P2 级: 死代码

| 类型 | 文件 | 说明 |
|------|------|------|
| 死类 | `academic/services/recommend/similarity.py` | `SimilarityCalculator` 仅测试引用，3/4 方法连测试都不调用 |
| 死方法 | `academic/services/recommend/recommend_service.py:460` | `generate_reasons` 无任何引用 |
| 死方法 | `academic/services/role_identifier.py:188,204` | `determine_role` / `determine_role_from_author` 无引用 |
| 死方法 | `shared/repositories/user_repository.py` | `get_with_scopes` 无调用者 |
| 死方法 | `academic/repositories/raw_data_repository.py` | `get_all_author_ids`, `count_by_status` 无调用者 |
| 死方法 | `academic/repositories/embedding_repository.py` | `get_all_by_talent_id` 无调用者 |

### 未用导入 (ruff F401)

| 文件 | 未用导入 |
|------|----------|
| `open_source/repositories/open_source/advanced.py` | `and_`, `cast`, `exists`, `or_`, `JSONB` |
| `open_source/repositories/open_source/core.py` | `json`, `re`, `text` |
| `shared/services/llm/llm_embedding_mixin.py` | `Any`, `APIConnectionError`, `AsyncOpenAI`, `with_timeout` |
| `open_source/api/developers.py` | `HTTPException` |
| `shared/services/llm/llm_gateway.py` | `asyncio` |
| `shared/services/system_config_test_service.py` | `time` |

> ruff check: 29 errors (全部为 F401/I001，可自动修复)

### 前端未用导入 (tsc --noEmit)

| 文件 | 未用导入 |
|------|----------|
| `pages/industry/industry-demo-page.tsx` | 6 个未用图标 |
| `pages/open-source/open-source-demo-page.tsx` | `Badge`, `CodeOutlined`, `ForkOutlined`, `LockOutlined` |

---

## P1 级: 魔法数字

| 值 | 位置 | 说明 |
|----|------|------|
| `6, 5, 5, 5, 10` | `homepage.py` 首页 limit (重复2次) | 应提取配置常量 |
| `0.7` | `os_developer_service.py:339,360` 相似度阈值 | 学术域用 settings，开源域硬编码 |
| `30.0` | `github_client.py:167` 超时 | 同文件 `__aenter__` 用 settings |
| `60` | 3个LLM服务工厂 `timeout or 60` | 与 `settings.LLM_TIMEOUT=30` 不一致 |
| `500` | `os_collection_service.py:491` 错误消息截断 | 无命名常量 |
| `0.8 / 0.5` | `author.py` normalizer confidence_score | 应为类常量 |
| `0.8` | `recommend_service.py` similarity_score 阈值 | 应为类常量 |

---

## P1 级: 错误处理不一致

| 模式 | 数量 | 位置 |
|------|------|------|
| 原始 `HTTPException` | 182+ | 几乎所有 API |
| `ValueError` / `RuntimeError` | 46 | services / repositories |
| 自定义 `AppException` 层次结构 | 仅 2 处 | 仅 `venue.py` |

**根因**: `core/exceptions.py` 定义了完善的 `AppException`/`NotFoundError`/`BadRequestError` 体系 + 全局异常处理器，但几乎未被使用。Service 层抛的 `ValueError` 在 API 层如未 catch 就变 500。

---

## 汇总

| 级别 | 数量 | 代表性问题 |
|------|------|------------|
| **P0** | 2+24 | 巨型文件(1034行), 复杂函数(24个>15分支) |
| **P1** | 10+ | 命名不一致, 6种重复代码模式, 21个过长函数, 魔法数字, 错误处理不一致 |
| **P2** | 15+ | 死代码, 未用导入(29处ruff + 10处tsc) |
