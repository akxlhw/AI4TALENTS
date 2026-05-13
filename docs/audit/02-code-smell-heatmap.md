# Phase 2: 代码异味热力图 (v2.0.1 更新)

> 扫描时间：2026-05-12

## 1. 巨型文件 (>300行)

### 后端 Top 10

| 行数 | 文件 | 级别 |
|------|------|------|
| 847 | `shared/repositories/user_repository.py` | P1 |
| 786 | `academic/services/data_fetchers.py` | P1 |
| 767 | `shared/api/permissions.py` | P1 |
| 732 | `shared/api/system_config.py` | P1 |
| 702 | `academic/repositories/raw_data_repository.py` | P1 |
| 683 | `academic/repositories/talent/talent_search_repository.py` | P1 |
| 678 | `open_source/repositories/open_source/core.py` | P1 |
| 599 | `academic/api/collect.py` | P2 |
| 583 | `academic/services/collaboration_service.py` | P2 |
| 572 | `shared/services/config_service.py` | P2 |

> 后端 >300行文件: 24个; >500行: 8个

### 前端 Top 5

| 行数 | 文件 | 级别 |
|------|------|------|
| 1034 | `system-config/components/collect-config-tab.tsx` | **P0** |
| 707 | `user/favorites-page.tsx` | P1 |
| 585 | `admin/admin-page.tsx` | P1 |
| 546 | `types/index.ts` | P2 |
| 544 | `admin/data-version-page.tsx` | P2 |

## 2. 过长函数 (>100行)

| 估计行数 | 函数 | 文件 | 级别 |
|----------|------|------|------|
| ~219 | `test_proxy_connection` | `system_config.py` | **P0** |
| ~147 | `compute_selected_works_for_all_authors` | `data_fetchers.py` | P1 |
| ~140 | `fetch_authors_by_ids` | `data_fetchers.py` | P1 |
| ~139 | `execute_task` | `orchestrator.py` | P1 |
| ~133 | `get_talent_list_by_cursor` | `tech_domain_repository.py` | P1 |
| ~129 | `get_talent_list` | `tech_domain_repository.py` | P1 |
| ~975 | `CollectConfigTab` 组件 | `collect-config-tab.tsx` | **P0** |

## 3. 死代码

### 后端 (0调用者 Repository 方法)

| 方法 | 文件 | 级别 |
|------|------|------|
| `UserRepository.get_with_scopes` | `user_repository.py` | P1 |
| `RawWorkRepository.get_all_author_ids` | `raw_data_repository.py` | P1 |
| `RawAuthorRepository.count_by_status` | `raw_data_repository.py` | P1 |
| `EmbeddingRepository.get_all_by_talent_id` | `embedding_repository.py` | P1 |

### 前端 (0调用者 导出函数)

| 函数 | 文件 | 级别 |
|------|------|------|
| `getFollowupStatusText` | `followupStatus.ts` | P2 |
| `getFollowupStatusColor` | `followupStatus.ts` | P2 |
| `isValidRoleType` | `roleType.ts` | P2 |
| `getRoleTypeOptions` | `roleType.ts` | P2 |

## 4. 魔法数字

| 值 | 位置 | 级别 |
|----|------|------|
| `6, 5, 5, 5, 10` | homepage.py 首页硬编码 limit (重复2次) | P1 |
| `0.8 / 0.5` | author.py normalizer confidence_score | P2 |
| `0.8` | recommend_service.py similarity_score 阈值 | P2 |
| `30` | data_fetchers.py refresh_days 默认值 | P2 |
| `16 / 64` | embedding_domain_service.py batch_size 限制 | P2 |

> 对比: `role_identifier.py` 正确使用 `PROFESSOR_H_INDEX_HIGH = 25` 等类常量

## 5. 错误处理不一致 (P1)

| 模式 | 数量 | 位置 |
|------|------|------|
| 原始 `HTTPException` | 182 | 几乎所有 API |
| `ValueError` / `RuntimeError` | 46 | services / repositories |
| 自定义 `AppException` 层次结构 | 仅 2 处 | 仅 `venue.py` |

**核心问题**: `core/exceptions.py` 定义了完善的 `AppException`/`NotFoundError`/`BadRequestError` 体系 + 全局异常处理器，但几乎没有被使用。Service 层抛的 `ValueError` 在 API 层如未 catch 就变 500。

## 6. `_and_commit` 重复 (P2)

`user_repository.py` 有 11 对方法：`create_user` + `create_user_and_commit`，后者仅多一行 `session.commit()`。应通过 Unit of Work 或 Service 层 commit 策略统一。

---

## 汇总

| 级别 | 数量 | 代表性问题 |
|------|------|------------|
| **P0** | 2 | 1034行组件、219行函数 |
| **P1** | 10 | 长函数、死代码、错误处理不一致、首页魔法数字 |
| **P2** | 14 | 魔法数字阈值、未使用导出、_and_commit重复 |
