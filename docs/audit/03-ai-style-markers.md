# Phase 3: AI 生成代码特征识别 (全面审计)

> 审计时间：2026-05-15

## 1. 过度冗长

### 1.1 合作关系创建逻辑4重重复

**文件**: `academic/services/collaboration_service.py`

`_create_collaborations_with_cache` (252-327) 与 `_create_collaborations` (201-250) 近乎逐字重复。年更新逻辑在两方法中出现 **4 次**:

```python
# 行 279-289 (缓存分支)
if collab.first_collaboration_year:
    collab.first_collaboration_year = min(collab.first_collaboration_year, publication_year)
    collab.last_collaboration_year = max(collab.last_collaboration_year, publication_year)
else:
    collab.first_collaboration_year = publication_year
    collab.last_collaboration_year = publication_year

# 行 300-311 (未缓存分支) —— 完全相同
```

**重构建议**: 提取 `_update_collaboration_years(collab, year)` + `_upsert_collaboration(t1, t2, cache, year)`。

### 1.2 `parse_jd_with_fallback` 纯透传

**文件**: `shared/services/llm/llm_gateway.py:277-292`

```python
async def parse_jd_with_fallback(self, jd_text: str) -> JDFeatures:
    """v1.4.1: 移除 fallback..."""
    return await self.parse_jd(jd_text)
```

方法体仅一行委托，15 行 docstring 描述已不存在的行为。

**重构建议**: 删除方法，调用方直接使用 `parse_jd`。

### 1.3 `get_sync_status` 加载全表到内存

**文件**: `academic/services/collaboration_service.py:549-555`

```python
stmt = select(Collaboration)
result = await self.session.execute(stmt)
for collab in result.scalars().all():
    talents_with_collab.add(collab.talent_id_1)
    talents_with_collab.add(collab.talent_id_2)
```

**重构建议**: 使用 SQL `COUNT(DISTINCT ...)` + `UNION` 子查询。

### 1.4 纯委托门面类

**文件**: `open_source/services/open_source_service.py` (302行, 47方法)

100% 方法均为透传至子服务，零业务逻辑。302 行纯样板代码。

**重构建议**: 删除门面类，API 层直接注入子服务。

### 1.5 `_and_commit` 方法对

**文件**: `shared/repositories/user_repository.py` (11对方法)

`create_user` + `create_user_and_commit`，后者仅多一行 `session.commit()`。

**重构建议**: 采用 Unit of Work 模式，由 Service 层控制 commit 时机。

---

## 2. 无意义注释

### 2.1 "描述 WHAT 而非 WHY" (collaboration_service.py 重灾区)

| 行号 | 注释 | 问题 |
|------|------|------|
| 89 | `# 1. 构建作者 OpenAlex ID -> talent_id 映射` | 方法名 `_build_talent_id_map` 已说明 |
| 138 | `# 获取发表年份` | 变量名 `pub_year` 已说明 |
| 217 | `# 检查合作关系是否已存在` | 代码执行的就是查询 |
| 239 | `# 创建新的合作关系` | `Collaboration(...)` 已经说明 |
| 396 | `# 获取该学者的所有合作关系` | 查询语句已说明 |
| 416 | `# 获取主学者信息（预加载 school 关系）` | 代码已说明 |
| 562 | `# 获取最后同步时间` | 函数调用已说明 |

**统计**: `collaboration_service.py` 中有 ~10 处纯复述注释。

### 2.2 嵌入服务步骤注释

**文件**: `academic/services/embedding/embedding_service.py`

- 行 89: `# 检查人才是否存在` ❌ — 代码自明
- 行 94: `# 检查数据库` ❌ — 代码自明
- 行 180: `# 获取人才信息（一次性获取，用于两种向量类型）` ✅ — 解释了设计意图

### 2.3 其他无意义注释

| 文件 | 行号 | 注释 |
|------|------|------|
| `shared/services/llm/retry.py` | 58 | `# 检查是否可重试` — `if not e.is_retryable()` 自明 |
| `shared/services/llm/retry.py` | 62 | `# 计算延迟` — 下方代码自明 |
| `shared/services/llm/llm_gateway.py` | 175 | `# 检查缓存` — `if self.cache:` 自明 |
| `pages/academic/academic-country-school-page.tsx` | 40 | `// 定义各区域的国家代码集合` — 变量名已说明 |
| `pages/academic/academic-country-school-page.tsx` | 111 | `// 初始化加载` — `useEffect` 自明 |

---

## 3. 硬编码魔法值

### 3.1 GitHub Client 超时不一致

**文件**: `open_source/services/github_client.py:167`

```python
timeout=30.0,  # 硬编码！同文件 __aenter__ 使用 settings.HTTP_TIMEOUT_DEFAULT
```

### 3.2 LLM 超时回退值散布 3 文件

| 文件 | 行号 | 硬编码 |
|------|------|--------|
| `academic/services/jd_match/jd_match_service.py` | 165 | `timeout=llm_config.timeout or 60` |
| `academic/services/search/search_service.py` | 109 | `timeout=llm_config.timeout or 60` |
| `open_source/services/os_developer_service.py` | 305 | `timeout=llm_config.timeout or 60` |

`settings.LLM_TIMEOUT` 默认 30.0，硬编码回退 60，二者不一致。

### 3.3 相似度阈值硬编码

**文件**: `open_source/services/os_developer_service.py:339,360`

```python
similarity_threshold=0.7,  # 学术域用 settings (0.5/0.6)，开源域硬编码
```

### 3.4 首页限制数量重复

**文件**: `academic/api/homepage.py:55-61,87-93`

5 行相同代码出现两次 (正常+降级路径)，魔法数字 6/5/5/10 无命名常量。

### 3.5 错误消息截断长度

**文件**: `open_source/services/os_collection_service.py:491`

```python
task.error_message = str(e)[:500]  # 500 为魔法数字
```

---

## 4. 错误处理精神分裂

### 4.1 ValueError + 字符串匹配翻译

**文件**: `academic/services/venue_service.py` + `academic/api/venue.py:56-59`

Service 层: `raise ValueError("Venue not found")`
API 层: `if "not found" in str(e).lower(): raise NotFoundError(...)` — **字符串匹配路由状态码！**

### 4.2 33 处裸 HTTPException

| 文件 | 数量 | 说明 |
|------|------|------|
| `shared/api/auth.py` | 18 | 绕过 AppException 体系，无 request_id |
| `shared/api/permissions.py` | 15 | 同上 |
| 其他 API 文件 | 149+ | 几乎全部使用 HTTPException |

对比: 项目自身的 `AppException` 体系仅被 `venue.py` 使用。

### 4.3 CacheService 返回值语义不一致

| 方法 | 错误返回 | 类型 |
|------|----------|------|
| `get()` | `None` | `T | None` |
| `set()` | `False` | `bool` |
| `delete()` | `False` | `bool` |
| `delete_pattern()` | `0` | `int` |
| `incr()` | `None` | `int | None` |

### 4.4 向量搜索失败静默返回空列表

**文件**: `academic/services/recommend/recommend_service.py:305-307`

```python
except Exception as e:
    logger.warning(f"Vector similarity search failed: {e}")
    return []  # 调用方无法得知搜索降级
```

### 4.5 脆弱的错误消息路由

**文件**: `open_source/api/repo_config.py:71-72`

```python
raise HTTPException(status_code=400 if "format" in str(e) or "tech_element" in str(e) else 409, ...)
```

重命名错误消息会悄悄改变 API 行为。"developer_ids must contain 2 to 5 items" 这种验证错误被映射为 404 而非 400。

---

## 5. 过度防御

### 5.1 `.get("field", 0) or 0` 双重空值守卫 (10+ 处)

**文件**: `open_source/services/collectors/github_collector.py`

```python
stars = repo_info.get("stargazers_count", 0) or 0     # 行 85
forks = repo_info.get("forks_count", 0) or 0           # 行 86
"followers_count": user.get("followers", 0) or 0,       # 行 263
```

`.get("field", 0)` 已处理 key 缺失，`or 0` 仅在 API 返回 None 时有用，双守卫冗余。

**重构建议**: 创建 `_safe_int(value, default=0)` 辅助函数。

### 5.2 CacheService 8 次重复的 `if not self._client` 检查

**文件**: `shared/services/cache_service.py` (行 90, 120, 151, 172, 250, 277, 305, 327)

每个方法首行都有相同检查。`_client` 构造后不变。

**重构建议**: 使用 `@_require_client` 装饰器或 `NullCacheService` 空对象模式。

### 5.3 嵌入维度回退值不一致

**文件**: `academic/services/embedding/embedding_service.py:348-349,372`

```python
dim = self.dimension or 1024  # 硬编码 1024 ≠ settings.EMBEDDING_DIMENSION(1536)
```

### 5.4 逐字段 `is not None` 赋值

**文件**: `shared/repositories/user_repository.py:836-843`

```python
if display_name is not None:
    user.display_name = display_name
if email is not None:
    user.email = email
# ... 继续 11 个字段
```

**重构建议**: `model_dump(exclude_unset=True)` + 批量更新。

### 5.5 `scalar() or 0` 重复 15+ 处

**文件**: `academic/builders/stat_builder.py:104-258`

**重构建议**: 提取 `scalar_or_zero()` 辅助方法。

---

## 汇总

| 特征 | 严重度 | 发现数 | 最严重文件 |
|------|--------|--------|-----------|
| 过度冗长 | P1 | 5 | `collaboration_service.py` (4重重复) |
| 无意义注释 | P2 | ~30 | `collaboration_service.py` (10+ 条) |
| 硬编码魔法值 | P1 | 10+ | `homepage.py`, `github_client.py`, 3个LLM工厂 |
| 错误处理不一致 | **P1** | 182+ | `auth.py`/`permissions.py` (33处裸 HTTPException) |
| 过度防御 | P2 | 8+ | `github_collector.py` (10+ 处 `or 0`), `cache_service.py` (8处守卫) |
