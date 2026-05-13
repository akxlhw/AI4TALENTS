# Phase 3: AI 生成代码特征识别 (v2.0.1 更新)

> 扫描时间：2026-05-12

## 1. 无意义注释 (P2)

**模式**: 注释只复述代码行为，未解释"为什么"。

**典型示例**:

| 文件 | 行号 | 注释 | 问题 |
|------|------|------|------|
| `collaboration_service.py` | 138 | `# 获取发表年份` | 代码 `publication_year = ...` 已自明 |
| `collaboration_service.py` | 225 | `# 更新现有合作关系` | `existing.collaboration_count += 1` 自明 |
| `collaboration_service.py` | 239 | `# 创建新的合作关系` | `Collaboration(...)` 自明 |
| `collaboration_service.py` | 396 | `# 获取该学者的所有合作关系` | `select(Collaboration)...` 自明 |
| `embedding_repository.py` | 485 | `# 返回缺失的 ID` | `return missing_ids` 自明 |
| `embedding_service.py` | 180 | `# 获取人才信息（一次性获取，用于两种向量类型）` | 有价值 — 保留了"为什么" |
| `embedding_service.py` | 229 | `# 获取已有嵌入的人才（如果不强制重新生成）` | 有价值 — 保留了条件逻辑意图 |

**统计**: `collaboration_service.py` 中有 ~10 处纯复述注释，是重灾区。

**建议**: 删除纯复述注释，保留解释意图/约束的注释。

## 2. 硬编码超时与魔法值 (P2)

### 硬编码超时

| 文件 | 行号 | 值 | 上下文 |
|------|------|-----|--------|
| `openalex_client.py` | 59 | `timeout=30` | 构造函数默认值 |
| `github_client.py` | 167 | `timeout=30.0` | `_get()` 方法 |
| `system_config.py` | 406 | `timeout=30.0` | proxy 测试 |
| `system_config.py` | 488 | `timeout=10.0` | GitHub 测试 |
| 多个 LLM 调用 | — | `timeout=llm_config.timeout or 60` | 60 为 fallback 默认值 |

> `llm_config.timeout or 60` 模式在 5 处重复出现，fallback 值 60 应提取为常量。

### 魔法阈值

已在 Phase 2 中详述 (0.8/0.5 confidence_score, 相似度阈值等)。

## 3. 错误处理精神分裂 (P1)

**模式**: 同一项目内三种错误处理策略并行，使用不一致。

| 策略 | 数量 | 代表位置 |
|------|------|----------|
| 原始 `HTTPException` | 182 | 几乎所有 API |
| Python 内置 `ValueError`/`RuntimeError` | 46 | services / repositories |
| 自定义 `AppException` 体系 | 仅 2 处 | 仅 `venue.py` |

**同一文件混用示例**: `academic/api/talents.py` — 对认证用 `HTTPException`，对业务异常也用 `HTTPException`，未使用 `core/exceptions.py` 定义的 `NotFoundError`/`BadRequestError`。

**根因**: `core/exceptions.py` 和全局异常处理器在 v1.0 就定义好了，但后续开发全部使用了更"方便"的 `HTTPException`，自定义异常体系被架空。

## 4. 过度防御代码 (P2)

| 文件 | 行号 | 代码 | 评估 |
|------|------|------|------|
| `system_config.py` | 595-600 | Pydantic 字段逐个 `is not None` 检查 | **过度** — 应用 `model_dump(exclude_unset=True)` |
| `user_repository.py` | 836-843 | `if display_name is not None:` 逐字段赋值 | **过度** — 应提取通用 apply_updates |
| 多个 Repository | — | `list(result.scalars().all())` (10+处) | **冗余** — `all()` 已返回列表 |
| `stat_builder.py` | 104-258 | `scalar() or 0` 重复 15+次 | **冗余** — 应提取 `scalar_or_zero()` 辅助 |
| `academic-talent-detail-page.tsx` | 278 | 3条件互斥显示 | 合理 |
| `open-source-developer-detail-page.tsx` | 181 | 角色层级显示 | 合理 |

## 5. 错误处理的脆弱路由 (P1)

**额外发现**: Open Source API 层通过字符串匹配 `ValueError` 消息来决定 HTTP 状态码：

`repo_config.py:71-72`:
```python
except ValueError as e:
    raise HTTPException(status_code=400 if "format" in str(e) or "tech_element" in str(e) else 409, ...)
```

`developers.py:93-94`:
```python
except ValueError as e:
    raise HTTPException(status_code=404, detail=str(e)) from e
```

**问题**: 重命名错误消息会悄悄改变 API 行为。"developer_ids must contain 2 to 5 items" 这种验证错误被映射为 404 而非 400。

**修复**: Service 层应抛出语义化异常 (`ValidationError`, `NotFoundError`, `ConflictError`)，API 层根据异常类型自动路由状态码。

## 6. `_and_commit` 重复模式 (P2)

`user_repository.py` 有 11 对方法：`create_user` + `create_user_and_commit`，后者仅多一行 `session.commit()`。这是典型的 AI 生成"保险式"代码 — 为每个操作都提供"自动提交"变体。

**正确模式**: 使用 Unit of Work 模式或让 Service 层控制 commit 时机。`create_user_and_commit` 的调用者应统一为 Service 层，由 Service 在事务边界 commit。

---

## 汇总

| 特征 | 严重度 | 影响 |
|------|--------|------|
| 无意义注释 | P2 | ~30处，代码噪音 |
| 硬编码超时/魔法值 | P2 | 10+不同超时值，难以全局调优 |
| 错误处理不一致 | **P1** | 182 HTTPException vs 46 ValueError，脆弱的字符串路由 |
| 过度防御 | P2 | 逐字段 is not None，冗余 list() 包装 |
| `_and_commit` 重复 | P2 | 11对重复，代码膨胀 |
| 冗余 `scalar() or 0` | P2 | 15+处重复，应提取辅助 |
