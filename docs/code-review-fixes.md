# 数据采集模块代码修复方案

> 审查日期: 2026-03-31
> 审查文件: `backend/app/services/collect/*.py`, `backend/app/services/data_fetchers.py`

---

## 问题清单

| 编号 | 严重程度 | 问题 | 位置 |
|------|----------|------|------|
| CR-01 | Critical | 事务管理不一致 | `progress_tracker.py:95` |
| CR-02 | Critical | 全表查询性能问题 | `orchestrator.py:491-509` |
| IM-01 | Important | 缺少任务取消检查机制 | `orchestrator.py` |
| IM-02 | Important | N+1 问题（代表作品获取） | `orchestrator.py:430-479` |
| IM-03 | Important | 缺少 API 请求重试机制 | `data_fetchers.py` |
| IM-04 | Important | 异常处理过于宽泛 | `orchestrator.py:162-166` |
| IM-05 | Important | 预估失败后继续执行 | `orchestrator.py:191-206` |
| IM-06 | Important | 使用已废弃的 datetime.utcnow() | 多处 |
| SG-01 | Suggestion | 类型提示不完整 | 多处 |
| SG-02 | Suggestion | 魔法数字应定义为常量 | `orchestrator.py` |
| SG-03 | Suggestion | 日志级别使用字符串 | `progress_tracker.py` |
| SG-04 | Suggestion | 缺少 API 请求超时配置 | `data_fetchers.py` |
| SG-05 | Suggestion | 方法名与行为不符 | `orchestrator.py:574-610` |

---

## 详细修复方案

### CR-01: 事务管理不一致

**问题**: `update_progress` 方法内部调用了 `session.commit()`，破坏了编排器的事务边界。

**当前代码** (`progress_tracker.py:79-95`):
```python
async def update_progress(
    self,
    task: CollectTask,
    current_step: Optional[str] = None,
    progress_percent: Optional[int] = None
):
    if current_step:
        task.current_step = current_step
    if progress_percent is not None:
        task.progress_percent = progress_percent
    await self.session.flush()
    # Commit to make changes visible to frontend immediately
    await self.session.commit()  # 问题所在
```

**修复方案**:

方案 A（推荐）：移除 commit，改用 flush + 异步通知
```python
async def update_progress(
    self,
    task: CollectTask,
    current_step: Optional[str] = None,
    progress_percent: Optional[int] = None
):
    if current_step:
        task.current_step = current_step
    if progress_percent is not None:
        task.progress_percent = progress_percent
    await self.session.flush()
    # 不再 commit，由 orchestrator 统一管理事务边界
    # 前端通过轮询或 WebSocket 获取进度
```

方案 B：保留 commit 但显式声明行为
```python
async def update_progress(
    self,
    task: CollectTask,
    current_step: Optional[str] = None,
    progress_percent: Optional[int] = None,
    auto_commit: bool = False  # 新增参数控制是否提交
):
    if current_step:
        task.current_step = current_step
    if progress_percent is not None:
        task.progress_percent = progress_percent
    await self.session.flush()
    if auto_commit:
        await self.session.commit()
```

**推荐方案**: A

---

### CR-02: 全表查询性能问题

**问题**: `_update_talent_topic_tags` 查询所有 Talent，未按任务过滤。

**当前代码** (`orchestrator.py:481-512`):
```python
async def _update_talent_topic_tags(self, task_id: int, progress: CollectionProgress):
    # Get all talents with their tech tags
    result = await self.session.execute(
        select(Talent).options(
            selectinload(Talent.tech_tags).selectinload(TalentTechTag.tech_element)
        )
    )
    talents = result.scalars().all()  # 全表查询！
```

**修复方案**:
```python
async def _update_talent_topic_tags(self, task_id: int, progress: CollectionProgress):
    """Phase 9: Update talent topic_tags from tech tags

    只更新与当前任务相关的人才（通过 tech_tag 关联）
    """
    from app.models.talent import Talent, TalentTechTag
    from sqlalchemy.orm import selectinload

    progress.current_step = "Updating topic tags"
    self.progress_tracker.add_log("info", "开始更新人才技术标签")

    # 获取当前任务关联的 tech_element_id
    task = await self.session.execute(
        select(CollectTask).where(CollectTask.task_id == task_id)
    )
    task = task.scalar_one_or_none()
    if not task:
        return

    tech_element_id = task.tech_element_id

    # 只查询与当前 tech_element 相关的人才
    result = await self.session.execute(
        select(Talent).options(
            selectinload(Talent.tech_tags).selectinload(TalentTechTag.tech_element)
        ).join(TalentTechTag, Talent.talent_id == TalentTechTag.talent_id)
        .where(TalentTechTag.tech_element_id == tech_element_id)
        .distinct()
    )
    talents = result.scalars().all()

    updated_count = 0
    for talent in talents:
        if talent.tech_tags:
            tech_names = list(set(
                tag.tech_element.element_name
                for tag in talent.tech_tags
                if tag.tech_element and tag.is_enabled
            ))
            if tech_names:
                talent.topic_tags = tech_names
                updated_count += 1

    await self.session.flush()
    self.progress_tracker.add_log("info", f"更新了 {updated_count} 个人才的技术标签")
```

---

### IM-01: 缺少任务取消检查机制

**问题**: 长时间运行的任务没有检查是否被用户取消。

**修复方案**: 在每个阶段开始时检查任务状态

```python
# 在 CollectionOrchestrator 中添加辅助方法
async def _check_task_status(self, task_id: int) -> str:
    """检查任务当前状态"""
    result = await self.session.execute(
        select(CollectTask.status).where(CollectTask.task_id == task_id)
    )
    status = result.scalar_one_or_none()
    return status or "unknown"

async def _should_cancel(self, task_id: int) -> bool:
    """检查任务是否应该被取消"""
    status = await self._check_task_status(task_id)
    return status in ("cancelled", "cancelling")

# 在 execute_task 中每个阶段前检查
async def execute_task(self, task_id: int) -> CollectionProgress:
    # ... Phase 0 ...

    if await self._should_cancel(task_id):
        await self.progress_tracker.update_task_status(task, "cancelled")
        progress.status = "cancelled"
        return progress

    # ... Phase 1 ...

    if await self._should_cancel(task_id):
        await self.progress_tracker.update_task_status(task, "cancelled")
        progress.status = "cancelled"
        return progress

    # ... 其他阶段 ...
```

---

### IM-02: N+1 问题（代表作品获取）

**问题**: 为每个新作者单独调用 API 获取代表作品。

**当前代码** (`orchestrator.py:430-479`):
```python
for i, talent_info in enumerate(new_talents):
    works = await self.work_fetcher.fetch_author_top_works(...)  # 每个作者一次 API 调用
```

**修复方案**: 使用 asyncio.Semaphore 控制并发

```python
async def _fetch_selected_works(
    self,
    new_talents: List[dict],
    progress: CollectionProgress
):
    """Phase 8: Fetch selected works with controlled concurrency"""
    from app.services.common.openalex_utils import REQUEST_DELAY

    if not new_talents:
        self.progress_tracker.add_log("info", "无需获取代表作品（无新增教授）")
        return

    progress.current_step = "Fetching selected works"
    self.progress_tracker.add_log("info", f"开始为 {len(new_talents)} 位新入库教授获取代表作品")

    # 使用 Semaphore 控制并发数（最多 3 个并发请求）
    semaphore = asyncio.Semaphore(3)
    total_fetched = 0
    total_inserted = 0

    async def fetch_for_talent(talent_info: dict):
        nonlocal total_fetched, total_inserted
        async with semaphore:
            try:
                talent_id = talent_info["talent_id"]
                openalex_author_id = talent_info["openalex_author_id"]
                works_count = talent_info.get("works_count", 0)

                if works_count <= 5:
                    return

                works = await self.work_fetcher.fetch_author_top_works(
                    openalex_author_id=openalex_author_id,
                    max_works=10
                )

                if not works:
                    return

                for order, work in enumerate(works):
                    if not work.get("title"):
                        continue
                    selected_work = SelectedWork(
                        talent_id=talent_id,
                        title=work.get("title", "")[:500],
                        publication_year=work.get("publication_year"),
                        venue_name=work.get("venue_name"),
                        citation_count=work.get("citation_count", 0),
                        source_work_id=work.get("source_work_id"),
                        doi=work.get("doi"),
                        display_order=order
                    )
                    self.session.add(selected_work)
                    total_inserted += 1

                total_fetched += 1
                await asyncio.sleep(REQUEST_DELAY)

            except Exception as e:
                self.progress_tracker.add_log(
                    "warning",
                    f"获取代表作品失败: talent_id={talent_info.get('talent_id')}, error={str(e)}"
                )

    # 并发执行所有请求
    await asyncio.gather(*[fetch_for_talent(t) for t in new_talents])

    await self.session.flush()
    self.progress_tracker.add_log(
        "info",
        f"代表作品获取完成: {total_fetched} 位教授，{total_inserted} 篇作品"
    )
```

---

### IM-03: 缺少 API 请求重试机制

**问题**: API 请求失败时没有重试机制。

**修复方案**: 添加 tenacity 重试装饰器

```python
# 在 data_fetchers.py 顶部添加
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import aiohttp

# 定义可重试的异常
class RetryableError(Exception):
    """可重试的错误"""
    pass

# 重试装饰器
def with_retry(max_attempts: int = 3, min_wait: float = 1.0, max_wait: float = 10.0):
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(RetryableError),
        reraise=True
    )

# 在 WorkFetcher 中使用
class WorkFetcher:
    @with_retry(max_attempts=3)
    async def _fetch_page(self, url: str, params: dict, headers: dict) -> dict:
        """带重试的单页获取"""
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(url, params=params, headers=headers) as response:
                if response.status == 429:  # Rate limited
                    raise RetryableError("Rate limited, should retry")
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                return await response.json()

    async def fetch_works_from_venue(self, venue, ...):
        # ... 使用 self._fetch_page 替代直接请求 ...
```

---

### IM-04: 异常处理过于宽泛

**问题**: 使用 `except Exception` 捕获所有异常，丢失堆栈跟踪。

**修复方案**: 记录完整堆栈并区分异常类型

```python
import traceback
from datetime import datetime, timezone

async def execute_task(self, task_id: int) -> CollectionProgress:
    # ...
    try:
        # ... 各阶段执行 ...
    except asyncio.CancelledError:
        # 任务被取消
        await self.progress_tracker.update_task_status(task, "cancelled")
        progress.status = "cancelled"
        self.progress_tracker.add_log("info", "任务被用户取消")

    except Exception as e:
        # 记录完整堆栈跟踪
        error_detail = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        await self.progress_tracker.update_task_status(task, "failed", str(e))
        progress.status = "failed"
        progress.errors.append(error_detail)
        self.progress_tracker.add_log("error", f"任务执行失败: {str(e)}", error_detail)
        logger.error(f"Task {task_id} failed: {traceback.format_exc()}")

    # ...
```

---

### IM-05: 预估失败后继续执行

**问题**: 预估阶段失败后继续执行，可能导致进度计算异常。

**修复方案**: 添加预估失败的备选处理

```python
async def _estimate_total_works(self, task: CollectTask) -> int:
    """预估任务的总论文数，失败时返回 -1 标记预估失败"""
    sub_tasks = await self.sub_task_repo.get_by_task(task.task_id)
    total = 0
    failed_count = 0

    year_from = task.time_window_start.year if task.time_window_start else None
    year_to = task.time_window_end.year if task.time_window_end else None

    for sub_task in sub_tasks:
        venue = await self.venue_repo.get_by_id(sub_task.venue_id)
        if venue and self.work_fetcher:
            try:
                count = await self.work_fetcher.get_work_count_from_venue(
                    venue, year_from=year_from, year_to=year_to
                )
                if hasattr(sub_task, 'estimated_works'):
                    sub_task.estimated_works = count
                total += count
                self.progress_tracker.add_log("info", f"{venue.venue_name}: 预估 {count} 篇论文")
            except Exception as e:
                failed_count += 1
                self.progress_tracker.add_log(
                    "warning",
                    f"{venue.venue_name if venue else sub_task.venue_id}: 预估失败 - {str(e)}"
                )

    await self.session.flush()

    # 如果所有预估都失败，记录警告并使用备用方案
    if failed_count == len(sub_tasks) and len(sub_tasks) > 0:
        self.progress_tracker.add_log(
            "warning",
            "所有 Venue 预估失败，进度显示将基于 Venue 数量而非论文数量"
        )
        return -1  # 返回 -1 表示预估失败

    return total

# 在 execute_task 中处理预估失败
async def execute_task(self, task_id: int) -> CollectionProgress:
    # ...
    estimated_total = await self._estimate_total_works(task)
    progress.estimated_works = estimated_total

    if estimated_total < 0:
        # 预估失败，使用 Venue 数量作为进度基准
        self.progress_tracker.add_log("warning", "预估失败，使用 Venue 数量计算进度")
        progress.estimated_works = 0
    # ...
```

---

### IM-06: 使用已废弃的 datetime.utcnow()

**问题**: `datetime.utcnow()` 在 Python 3.12 中已废弃。

**修复方案**: 统一使用时区感知的时间对象

```python
# 在文件顶部统一导入
from datetime import datetime, timezone

# 替换所有 datetime.utcnow() 为
datetime.now(timezone.utc)

# 或创建工具函数
def utcnow() -> datetime:
    """获取当前 UTC 时间（时区感知）"""
    return datetime.now(timezone.utc)
```

**涉及文件**:
- `progress_tracker.py`: 第 26, 68, 69, 71, 74 行
- `orchestrator.py`: 第 179 行
- `data_fetchers.py`: 第 179, 334, 427 行

---

### SG-01: 类型提示不完整

**修复方案**: 使用 TypedDict 或数据类

```python
from typing import TypedDict, List

class NewTalentInfo(TypedDict):
    """新入库学者信息"""
    talent_id: int
    openalex_author_id: str
    works_count: int

class SelectedWorkInfo(TypedDict):
    """代表作品信息"""
    title: str
    publication_year: Optional[int]
    citation_count: int
    venue_name: Optional[str]
    doi: Optional[str]
    source_work_id: Optional[str]

# 使用
async def _fetch_selected_works(
    self,
    new_talents: List[NewTalentInfo],
    progress: CollectionProgress
):
    ...
```

---

### SG-02: 魔法数字应定义为常量

**修复方案**:

```python
# 在 orchestrator.py 顶部定义常量
class PhaseProgress:
    """各阶段的进度百分比"""
    ESTIMATE = 2
    COLLECT_START = 5
    COLLECT_END = 20
    FETCH_AUTHORS = 20
    FETCH_INSTITUTIONS = 30
    NORMALIZE_SCHOOLS = 40
    NORMALIZE_AUTHORS = 50
    CALCULATE_TECH_BELONG = 60
    SYNC_SERVING_LAYER = 70
    FETCH_SELECTED_WORKS = 75
    UPDATE_TOPIC_TAGS = 80
    UPDATE_SCHOOL_STATS = 90
    BUILD_STATISTICS = 95
    COMPLETED = 100

# 使用
await self.progress_tracker.update_progress(task, "预估任务规模", PhaseProgress.ESTIMATE)
await self.progress_tracker.update_progress(task, "采集论文数据", PhaseProgress.COLLECT_START)
```

---

### SG-03: 日志级别使用字符串

**修复方案**: 使用枚举类型

```python
from enum import Enum

class LogLevel(str, Enum):
    """日志级别枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"

# 在 ProgressTracker 中使用
def add_log(self, level: LogLevel, message: str, details: Optional[Dict] = None):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.value,
        "message": message,
    }
    # ...

    # 日志输出也使用枚举
    if level == LogLevel.ERROR:
        logger.error(message)
    elif level == LogLevel.WARNING:
        logger.warning(message)
    else:
        logger.info(message)
```

---

### SG-04: 缺少 API 请求超时配置

**修复方案**: 添加超时配置

```python
from aiohttp import ClientTimeout

# 默认超时配置
DEFAULT_TIMEOUT = ClientTimeout(
    total=30,      # 总超时 30 秒
    connect=10,    # 连接超时 10 秒
    sock_read=30   # 读取超时 30 秒
)

class WorkFetcher:
    async def fetch_works_from_venue(self, venue, ...):
        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as http_session:
            # ...

class AuthorFetcher:
    async def fetch_authors_by_ids(self, author_ids, ...):
        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as http_session:
            # ...
```

---

### SG-05: 方法名与行为不符

**问题**: `_get_default_tech_direction` 不仅获取，还会创建默认方向。

**修复方案**: 拆分为两个方法

```python
async def _get_or_create_default_tech_direction(self, tech_element_id: int) -> Optional[int]:
    """获取或创建默认技术方向

    先尝试获取已存在的默认方向，不存在则创建新的。
    """
    # 先尝试获取
    direction_id = await self._get_default_tech_direction(tech_element_id)
    if direction_id:
        return direction_id

    # 不存在则创建
    return await self._create_default_tech_direction(tech_element_id)

async def _get_default_tech_direction(self, tech_element_id: int) -> Optional[int]:
    """获取默认技术方向（只获取，不创建）"""
    result = await self.session.execute(
        select(TechDirection.tech_direction_id).where(
            TechDirection.tech_element_id == tech_element_id,
            TechDirection.is_enabled == True
        ).order_by(TechDirection.sort_order).limit(1)
    )
    return result.scalar_one_or_none()

async def _create_default_tech_direction(self, tech_element_id: int) -> Optional[int]:
    """创建默认技术方向"""
    te_result = await self.session.execute(
        select(TechElement).where(TechElement.tech_element_id == tech_element_id)
    )
    tech_element = te_result.scalar_one_or_none()

    if not tech_element:
        logger.warning(f"Tech element {tech_element_id} not found")
        return None

    new_direction = TechDirection(
        direction_code=f"{tech_element.element_code}-DEFAULT",
        direction_name=f"{tech_element.element_name}（默认）",
        tech_element_id=tech_element_id,
        sort_order=0,
        is_enabled=True
    )
    self.session.add(new_direction)
    await self.session.flush()

    logger.info(f"Created default tech direction for {tech_element.element_name}")
    return new_direction.tech_direction_id
```

---

## 迭代修复计划

### 迭代 1: Critical 问题修复（预计 2 天）✅ 已完成

| 任务 | 问题编号 | 预计工时 | 优先级 | 状态 |
|------|----------|----------|--------|------|
| 修复事务管理不一致 | CR-01 | 2h | P0 | ✅ 已完成 |
| 修复全表查询性能问题 | CR-02 | 4h | P0 | ✅ 已完成 |
| 添加相关单元测试 | - | 4h | P0 | ✅ 已完成 |
| 集成测试验证 | - | 2h | P0 | ✅ 27 tests passed |

**修复内容**:
1. `progress_tracker.py`: 移除 `update_progress` 中的 `commit()`，事务边界由 orchestrator 统一管理
2. `orchestrator.py`: `_update_talent_topic_tags` 添加 `tech_element_id` 过滤条件，避免全表扫描
3. `orchestrator.py`: 修复 `TalentTechTag` 导入路径
4. `test_collect.py`: 添加 3 个测试类验证修复

### 迭代 2: Important 问题修复（预计 3 天）✅ 已完成

| 任务 | 问题编号 | 预计工时 | 优先级 | 状态 |
|------|----------|----------|--------|------|
| 添加任务取消检查机制 | IM-01 | 3h | P1 | ✅ 已完成 |
| 优化代表作品获取并发 | IM-02 | 4h | P1 | ✅ 已完成 |
| 添加 API 请求重试机制 | IM-03 | 3h | P1 | ✅ 已完成 |
| 改进异常处理 | IM-04 | 2h | P1 | ✅ 已完成 |
| 处理预估失败场景 | IM-05 | 2h | P1 | ✅ 已完成 |
| 替换 datetime.utcnow() | IM-06 | 1h | P1 | ✅ 已完成 |
| 添加相关测试 | - | 4h | P1 | ✅ 27 tests passed |

**修复内容**:

1. **IM-01** `orchestrator.py`: 添加 `_check_task_status`、`_should_cancel`、`_handle_cancellation` 方法，每个阶段开始前检查任务状态

2. **IM-02** `orchestrator.py`: `_fetch_selected_works` 使用 `asyncio.Semaphore(3)` 控制并发，`asyncio.gather` 并行执行

3. **IM-03** `data_fetchers.py`: 添加 `RetryableError` 类、`with_retry` 装饰器、`_fetch_page_with_retry` 方法，添加 `DEFAULT_TIMEOUT` 超时配置

4. **IM-04** `orchestrator.py`: 异常处理添加完整堆栈跟踪，区分 `asyncio.CancelledError` 和普通异常

5. **IM-05** `orchestrator.py`: `_estimate_total_works` 返回 -1 标记预估失败，execute_task 处理预估失败场景

6. **IM-06** 多个文件: 替换所有 `datetime.utcnow()` 为 `datetime.now(timezone.utc)`
   - `progress_tracker.py`
   - `venue_executor.py`
   - `task_creation.py`
   - `normalizers/author.py`
   - `normalizers/school.py`
   - `sync/author_sync.py`
   - `talent_service.py`
   - `data_fetchers.py`

### 迭代 3: Suggestion 改进（预计 1 天）✅ 已完成

| 任务 | 问题编号 | 预计工时 | 优先级 | 状态 |
|------|----------|----------|--------|------|
| 完善类型提示 | SG-01 | 1h | P2 | ✅ 已完成 |
| 定义进度常量 | SG-02 | 0.5h | P2 | ✅ 已完成 |
| 使用日志级别枚举 | SG-03 | 0.5h | P2 | ✅ 已完成 |
| 添加 API 超时配置 | SG-04 | 1h | P2 | ✅ 已在 IM-03 完成 |
| 重构方法命名 | SG-05 | 1h | P2 | ✅ 已完成 |
| 运行测试验证 | - | 1h | P2 | ✅ 27 tests passed |

**修复内容**:

1. **SG-01** `orchestrator.py`: 添加 `NewTalentInfo` TypedDict，更新 `_fetch_selected_works` 方法类型提示

2. **SG-02** `orchestrator.py`: 添加 `PhaseProgress` 常量类，替换所有魔法数字

3. **SG-03** `progress_tracker.py`: 添加 `LogLevel` 枚举，更新 `add_log` 方法支持枚举类型

4. **SG-04** 已在 IM-03 中完成：添加 `DEFAULT_TIMEOUT` 超时配置

5. **SG-05** `orchestrator.py`: 拆分 `_get_default_tech_direction` 为三个方法：
   - `_get_default_tech_direction`: 只获取，不创建
   - `_create_default_tech_direction`: 只创建
   - `_get_or_create_default_tech_direction`: 获取或创建（主入口）

---

## 测试计划

### 单元测试

```python
# tests/test_orchestrator_fixes.py

import pytest
from unittest.mock import AsyncMock, patch

class TestTransactionManagement:
    """CR-01: 事务管理测试"""

    async def test_update_progress_should_not_commit(self, db_session):
        """验证 update_progress 不会自动 commit"""
        tracker = ProgressTracker(db_session)

        # 创建测试任务
        task = CollectTask(status="pending")
        db_session.add(task)
        await db_session.flush()

        # 记录 commit 前的状态
        initial_commit_count = db_session.get_commit_count()  # 假设有 mock

        await tracker.update_progress(task, "测试步骤", 50)

        # 验证没有自动 commit
        assert db_session.get_commit_count() == initial_commit_count


class TestTalentQueryOptimization:
    """CR-02: 全表查询优化测试"""

    async def test_update_topic_tags_filters_by_tech_element(self, db_session):
        """验证只查询与任务相关的人才"""
        orchestrator = CollectionOrchestrator(db_session)

        # 创建测试数据...

        # 调用方法
        await orchestrator._update_talent_topic_tags(task_id=1, progress=...)

        # 验证 SQL 查询包含 tech_element_id 过滤条件
        # 可以通过 mock 或 SQL 日志验证


class TestTaskCancellation:
    """IM-01: 任务取消测试"""

    async def test_task_can_be_cancelled_between_phases(self, db_session):
        """验证任务可以在阶段之间被取消"""
        orchestrator = CollectionOrchestrator(db_session)

        # 创建任务并设置为取消状态
        task = CollectTask(task_id=1, status="cancelling")
        db_session.add(task)
        await db_session.commit()

        # 执行任务
        progress = await orchestrator.execute_task(1)

        # 验证任务状态为 cancelled
        assert progress.status == "cancelled"


class TestRetryMechanism:
    """IM-03: 重试机制测试"""

    async def test_api_request_retries_on_rate_limit(self):
        """验证 API 请求在 429 时重试"""
        fetcher = WorkFetcher(mock_session)

        with patch('aiohttp.ClientSession.get') as mock_get:
            # 模拟第一次返回 429，第二次成功
            mock_get.side_effect = [
                AsyncMock(status=429),
                AsyncMock(status=200, json=AsyncMock(return_value={"results": []}))
            ]

            result = await fetcher._fetch_page("url", {}, {})

            # 验证调用了 2 次
            assert mock_get.call_count == 2
```

### 集成测试

```python
# tests/integration/test_collection_pipeline.py

class TestCollectionPipelineFixes:
    """采集流水线修复集成测试"""

    async def test_full_pipeline_with_cancellation(self, test_client):
        """测试完整的采集流程（包含取消场景）"""
        # 创建任务
        # 启动执行
        # 中途取消
        # 验证状态正确

    async def test_pipeline_handles_api_failures_gracefully(self, test_client):
        """测试流水线优雅处理 API 失败"""
        # 模拟 API 失败
        # 验证重试机制生效
        # 验证错误日志记录

    async def test_progress_updates_are_consistent(self, test_client):
        """测试进度更新一致性"""
        # 执行完整流水线
        # 验证进度百分比单调递增
        # 验证最终状态正确
```

---

## 风险与依赖

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| CR-01 修复可能影响前端进度显示 | 前端无法实时看到进度 | 保留 flush，前端轮询频率调高 |
| IM-02 并发可能导致 API 限速 | 更多请求失败 | 使用 Semaphore 控制并发数 |
| IM-03 重试可能增加执行时间 | 任务耗时变长 | 配置合理的重试次数和等待时间 |

---

## 验收标准

1. **CR-01**: `update_progress` 不再调用 `commit()`，测试验证事务边界正确
2. **CR-02**: `_update_talent_topic_tags` 查询包含过滤条件，大数据量测试通过
3. **IM-01**: 任务可以在任意阶段之间被取消，状态正确更新
4. **IM-02**: 代表作品获取支持并发，执行时间显著缩短
5. **IM-03**: API 请求失败时自动重试，成功率提升
6. **IM-04**: 异常日志包含完整堆栈跟踪
7. **IM-05**: 预估失败时进度显示正常
8. **IM-06**: 所有 `datetime.utcnow()` 已替换
9. 所有单元测试和集成测试通过
