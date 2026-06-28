# 设计文档：官网人才采集（lab_web 域）

- **状态**：草案，待用户复核
- **日期**：2026-06-28
- **目标项目**：AI4TALENT（`D:\AI\AI4TALENT`）
- **范围标识**：`domains/lab_web/` 第一个 spec —— 骨架 + Stanford SAIL 端到端

---

## 1. 背景与目标

### 1.1 上下文

AI4TALENT（V2.2.0）是面向招聘团队的多维度人才发现平台，已有两个数据源域：

| 人才类型 | 数据来源 | 状态 |
|---------|---------|------|
| 学术人才 | OpenAlex 学术数据库 | ✅ 已完成（`domains/academic/`） |
| 开源人才 | GitHub 等开源社区 | ✅ 已完成（`domains/open_source/`） |
| 竞赛人才 | ICPC 等 | 📋 规划中 |
| **官网人才** | **顶尖 AI 实验室官网 People 页** | **本 spec 新增** |

两个现有数据源均基于结构化 API（OpenAlex、GitHub）。本 spec 新增第三个数据源域 **`lab_web`**，采集全球顶尖 AI 实验室官网 People 页的人才数据——这是 API 覆盖不到、需要网页爬虫的增量数据线。

### 1.2 用途（双目标）

1. **研究分析**：追踪人才在机构间的流动、研究领域分布、顶级实验室的人才集聚效应。重点是结构化字段。
2. **招聘线索**：联系方式（邮箱、个人主页）、当下角色与状态。数据需相对新鲜。

### 1.3 采集范围（第一版）

- 第一版：~10 个顶尖实验室（7–8 国外 + 1–2 国内），架构预留扩展到 50+。
- 数据源主次：官网 People 页为主，学术数据库与 LinkedIn 为辅（后两者留后续 spec）。
- **本 spec 只实现 Stanford SAIL 一个适配器**，其余 9 个只登记到注册表（`collector_class=null`）。

### 1.4 合规底线（B 方案）

技术合理范围内最大化覆盖，**不主动对抗反爬保护**：

- 尊重 robots.txt（被禁路径不抓取）。
- 诚实 UA、限速、并发上限。
- 不用 Scrapling 的 `StealthyFetcher`（主动反爬绕过）。遇 Cloudflare 类保护直接 `failed`，记录后人工评估。
- 不绕验证码、不模拟登录、不对抗 WAF。
- LinkedIn 留后续独立模块单独评估合规，本 spec 不涉及。

---

## 2. 总体方案

在 AI4TALENT 内新建第三个数据源域 `domains/lab_web/`，与 `academic`、`open_source` 并列，完整遵循 AI4TALENT 的 DDD 架构与既有铁律。

### 2.1 核心决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 数据落点 | raw 层（`lw_raw_person`）+ 复用 `core_talent` 服务层 | 对应 AI4TALENT 多层架构范式（如 `os_raw_developer` → `OSDeveloper`）；`core_talent` 字段已为官网数据预留；官网人才与学术人才进同一服务层，复用全部现有功能 |
| 采集器模式 | 抽象基类固化通用流程 + 子类填钩子 | 实验室页面结构差异大，纯配置撑不住；纯独立类重复多；基类+钩子是这类多源适配器最成熟的模式 |
| Scrapling 角色 | 仅用 `Fetcher`（单页抓取）+ `Selector`（解析） | Scrapling 的反爬/自适应能力是官网爬虫的核心价值；但不用其 `Spider` 并发框架（与 AI4TALENT 异步 ORM/`HttpClientFactory` 铁律冲突），改用 AI4TALENT 既有异步任务体系 |
| 数据更新 | 第一版一次性快照，raw 层只追加 | raw 层保留全部历史快照，为增量更新预留；调度后续加 |

### 2.2 第一版范围（本 spec 覆盖）

- `domains/lab_web/` 域骨架（api / models / schemas / repositories / services / constants，对齐 `open_source` 域结构）
- `lw_lab_registry` / `lw_raw_person` / `lw_collect_task` 三张表
- `SourceType.LAB_WEB` 枚举扩展
- 采集器抽象基类（固化通用流程 + 钩子）+ Scrapling 封装层
- Stanford SAIL 适配器（第一个完整实现）
- 采集任务编排 + raw → core_talent 同步服务
- 合规护栏（robots.txt、限速、UA、并发上限）
- 单元 + 集成测试

### 2.3 明确不在本 spec 范围（留后续 spec）

- 其他 9 个实验室的适配器实现（架构预留，逐个加）
- 学术数据增强（Semantic Scholar / DBLP）
- LinkedIn 采集器
- 跨源实体解析与去重、`unified_person_id` 的实际合并逻辑
- 定时调度 / 增量更新（raw 层设计预留）
- 前端页面（先跑通后端，前端留后续 spec）

---

## 3. 目录结构（新增部分）

```
backend/app/domains/lab_web/
├── __init__.py
├── api/
│   ├── __init__.py
│   └── collection.py                    # 触发采集、查任务状态（对齐 open_source/api/collection.py）
├── models/
│   ├── __init__.py
│   └── lab_web.py                       # LWLabRegistry, LWRawPerson, LWCollectTask
├── schemas/
│   ├── __init__.py
│   └── lab_web.py                       # Pydantic DTO
├── repositories/
│   ├── __init__.py
│   └── lab_web/
│       ├── __init__.py
│       └── core.py                      # LWRepository
├── services/
│   ├── __init__.py
│   ├── lw_collection_service.py         # 采集编排（对齐 os_collection_service.py）
│   ├── lw_person_service.py             # raw → core_talent 同步
│   └── collectors/
│       ├── __init__.py
│       ├── base_collector.py            # 抽象基类：固化流程 + 钩子
│       ├── scrapling_fetcher.py         # Scrapling Fetcher 封装
│       └── labs/
│           ├── __init__.py
│           └── stanford_sail.py         # SAIL 适配器
└── constants/
    ├── __init__.py
    └── role_mapping.py                  # 官网原始标题 → RoleType 标准化映射

# 既有文件改动（最小侵入）
backend/app/api_router.py                         # 注册 lab_web 路由
backend/app/model_registry.py                     # 注册 lab_web 模型（Alembic 能发现）
backend/app/domains/shared/models/enums.py        # 新增 SourceType.LAB_WEB
backend/migrations/versions/xxxx_add_lab_web_domain.py   # 新建表
backend/pyproject.toml                            # 新增 scrapling 依赖

# 测试
backend/tests/fixtures/lab_web/stanford_sail_people.html  # SAIL 页面快照
backend/tests/domains/lab_web/                              # 测试代码
```

---

## 4. 数据模型

遵循 AI4TALENT 命名约定（表名 `{module}_{entity}`，主键 `{entity}_id`，`TimestampMixin`），表前缀 `lw_` 与 `open_source` 的 `os_` 对称。

### 4.1 `lw_lab_registry`（实验室注册表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `lab_id` | Integer | PK, autoincrement | 主键 |
| `lab_code` | String(50) | unique, not null, index | 实验室短码，如 `stanford_sail`、`deepmind`，采集器调度键 |
| `lab_name` | String(255) | not null | 显示名，如 "Stanford AI Lab" |
| `lab_name_en` | String(255) | nullable | 英文名 |
| `institution` | String(255) | not null | 所属机构，如 "Stanford University" |
| `country` | String(50) | not null | 国家，用于后续国内外分布分析 |
| `people_url` | String(500) | not null | People 页入口 URL |
| `collector_class` | String(255) | nullable | 采集器类路径，如 `labs.stanford_sail.StanfordSailCollector`；null 表示尚未实现 |
| `fetch_mode` | String(20) | not null, default `'static'` | `static` / `dynamic`（决定用 Scrapling `Fetcher` 还是 `DynamicFetcher`） |
| `is_active` | Boolean | not null, default True | 是否启用采集 |
| `last_collected_at` | DateTime | nullable | 最近一次采集时间（为增量更新预留） |
| `notes` | Text | nullable | 备注（页面结构说明等） |
| `created_at` / `updated_at` | DateTime | `TimestampMixin` | 时间戳 |

第一版预置 ~10 行。SAIL 的 `collector_class` 填实际值，其余 9 个 `collector_class=null`。

### 4.2 `lw_raw_person`（原始层）

仿照 `os_raw_developer` 范式，保存官网解析的原始人员数据快照，支持解析回溯和增量对比。**raw 层只追加不覆盖**，保留全部历史快照。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `raw_id` | Integer | PK, autoincrement | 主键 |
| `lab_id` | Integer | FK → `lw_lab_registry.lab_id`, not null, index | 来源实验室 |
| `source_url` | String(500) | nullable | 该人员在官网的页面 URL |
| `name_raw` | String(255) | not null | 原始姓名（处理前） |
| `title_raw` | String(255) | nullable | 官网原始头衔原文，如 "PhD Candidate" |
| `email_raw` | String(255) | nullable | 原始邮箱（反混淆处理前） |
| `homepage_url` | String(500) | nullable | 个人主页 |
| `avatar_url` | String(500) | nullable | 头像 |
| `raw_data` | JSON | default dict | 完整原始字段快照（含未标准化额外字段），供回溯 |
| `fetched_at` | DateTime | default now | 抓取时间 |
| `collect_task_id` | Integer | nullable, index | 关联采集任务，便于追溯 |
| `content_hash` | String(64) | not null, index（**非唯一**） | 内容指纹，用于增量更新时判断"该人员上次到现在是否变化" |
| `created_at` | DateTime | default now | 创建时间 |

**只追加语义**：raw 层是真正的 append-only 快照层。每次采集为每个人员插入一行新快照，`content_hash` **不设唯一约束**——因为按 §6.5 设计，同一人跨次采集的哈希是稳定的，若设唯一约束会阻止跨次采集插入，破坏增量对比与回溯能力。

**增量对比原理**：取某 `(lab_id, name)`（或 `source_url`）的最新一条快照的 `content_hash`，与本次新算的 hash 比对——相同则"未变化"，不同则"人员信息变化"，从而支撑后续增量更新判断。

**同次采集内的去重**：在应用层完成，不靠 DB 约束。`LWRepository.upsert_raw_persons` 在插入前对 `drafts` 按 `content_hash` 去重（同一人在同次采集的页面里出现两次只插一行）。`content_hash` 的普通索引用于支撑跨次/跨人查询。`content_hash` 计算规则见 §6.5。

### 4.3 `lw_collect_task`（采集任务表）

完全复刻 `OSCollectTask` 字段结构。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `task_id` | Integer | PK, autoincrement | 主键 |
| `task_name` | String(255) | not null | 任务名 |
| `lab_id` | Integer | FK → `lw_lab_registry.lab_id`, not null | 目标实验室 |
| `status` | String(20) | not null, default `'pending'`, index | pending/running/success/failed/partial/cancelled |
| `progress_percent` | Integer | default 0 | 进度 |
| `current_step` | String(100) | nullable | 当前步骤描述 |
| `total_records` | Integer | default 0 | 预计/实际总人数 |
| `processed_records` | Integer | default 0 | 已处理人数 |
| `config_json` | JSON | default dict | 采集配置（fetch_mode、UA、限速参数等） |
| `error_message` | Text | nullable | 失败原因（截断到 `COLLECT_ERROR_MAX_LENGTH`） |
| `started_at` | DateTime | nullable | 开始时间 |
| `completed_at` | DateTime | nullable | 完成时间 |
| `created_by` | Integer | FK → `iam_user_account.user_id`, nullable | 触发者 |
| `created_at` / `updated_at` | DateTime | `func.now()` | 时间戳 |

### 4.4 枚举扩展

`backend/app/domains/shared/models/enums.py` 的 `SourceType` 新增：

```python
class SourceType(str, enum.Enum):
    OPENALEX = "openalex"
    MANUAL = "manual"
    IMPORT = "import"
    LAB_WEB = "lab_web"      # 新增：官网 People 页采集
```

### 4.5 与 `core_talent` 的衔接

`core_talent` 表**不加字段**（已预留：`source_type`、`source_record_id`、`lab_name`、`department_name`、`current_title`、`role_type`、`role_confidence`、`extra_data`）。同步规则：

| `core_talent` 字段 | 来源 |
|--------------------|------|
| `source_type` | `SourceType.LAB_WEB.value` |
| `source_record_id` | `lw_raw_person.content_hash`（利用已有 unique 约束） |
| `name` | `normalize_name(raw.name_raw)` |
| `name_en` | 拉丁字母部分（可识别时） |
| `current_title` | `raw.title_raw` |
| `lab_name` | `lab.lab_name` |
| `department_name` | `lab.institution` |
| `role_type` | `map_role_type(raw.title_raw)` |
| `role_confidence` | 上一步的置信度 |
| `extra_data` | `{homepage_url, avatar_url, email, source_url, title_raw}` |
| `visibility_status` | `VisibilityStatus.ACTIVE.value` |
| `is_visible` | `True` |

**跨源隔离铁律**：`lab_web` 域同步时**只 upsert `source_type='lab_web'` 的记录**，绝不动 `openalex` 来源记录（通过 `WHERE source_type='lab_web'` 限定查询范围）。

**跨源同人重复**（本 spec 明确不解决）：同一人可能在 `core_talent` 里既有 `lab_web` 又有 `openalex` 两条记录。这是预留的 `unified_person_id` 字段未来要解决的实体合并问题，本 spec 只保证同源不重复。

---

## 5. 采集器架构

### 5.1 采集流程全景（基类固化）

```
collect(ctx) 主流程
  │
  ├─ 1. 前置校验：lab.is_active? collector_class? fetch_mode?
  ├─ 2. 合规护栏：robots.txt 检查 people_url 是否允许
  ├─ 3. 抓取入口页：经 ScraplingFetcher（封装 Scrapling Fetcher/DynamicFetcher）
  ├─ 4. 解析人员卡片：调用钩子 parse_person_cards(response) → List[元素]
  ├─ 5. 分页处理：调用钩子 get_next_page_url(response) → url | None（循环回 step 3）
  ├─ 6. 逐人提取：对每个卡片调用钩子 extract_person(card) → RawPersonDraft
  ├─ 7. 标准化预处理：邮箱反混淆、姓名清洗、role_type 标准化（共享逻辑）
  ├─ 8. 批量入 raw 层：LWRepository.upsert_raw_persons（写 lw_raw_person，计算 content_hash）
  ├─ 9. 同步服务层：LWPersonService.sync_to_core_talent（raw → core_talent）
  └─ 10. 更新任务状态 + lab.last_collected_at
```

步骤 1/2/3/5/8/9/10 是**固定流程**（基类实现），步骤 4/6 是**钩子**（子类必须实现），步骤 5 是**可选钩子**，步骤 7 是共享工具函数。

### 5.2 抽象基类 `BaseLabCollector`

```python
# backend/app/domains/lab_web/services/collectors/base_collector.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import asyncio


@dataclass
class RawPersonDraft:
    """采集器钩子产出的中间结构，尚未入库。"""
    name_raw: str
    title_raw: str | None = None
    email_raw: str | None = None
    homepage_url: str | None = None
    avatar_url: str | None = None
    source_url: str | None = None
    extra: dict[str, Any] | None = None  # 实验室特有字段


@dataclass
class CollectContext:
    """单次采集运行的共享上下文。"""
    task_id: int
    lab_id: int
    cancelled: asyncio.Event = field(default_factory=asyncio.Event)


class BaseLabCollector(ABC):
    """实验室官网采集器抽象基类。
    子类只需实现 parse_person_cards / extract_person（必填），
    get_next_page_url（可选），其余抓取、合规、入库、同步流程由基类固化。
    """

    # 子类可覆盖的配置（有合理默认值）
    lab_code: str = ""              # 对应 lw_lab_registry.lab_code
    request_delay: float = 1.0      # 请求间隔（秒），合规限速
    max_pages: int = 50             # 分页保护上限

    def __init__(self, fetcher: "ScraplingFetcher", lab: "LWLabRegistry") -> None:
        self.fetcher = fetcher
        self.lab = lab

    async def collect(self, ctx: "CollectContext") -> None:
        """固化主流程，子类不应覆盖。"""
        # 上述 10 步的实现

    # ===== 子类必须实现的钩子 =====

    @abstractmethod
    def parse_person_cards(self, response: Any) -> list[Any]:
        """从页面响应中定位人员卡片元素列表。返回 Scrapling Selector 列表。"""

    @abstractmethod
    def extract_person(self, card: Any) -> RawPersonDraft:
        """从单个卡片提取人员字段，返回未标准化的 RawPersonDraft。"""

    def get_next_page_url(self, response: Any) -> str | None:
        """分页钩子。默认返回 None（无分页），有分页的实验室覆盖此方法。"""
        return None
```

### 5.3 Scrapling 封装层 `ScraplingFetcher`

Scrapling 库与 AI4TALENT 架构铁律之间的桥。处理两个关键点：(1) 配置统一（遵守"出站 HTTP 经 `HttpClientFactory`"的精神）；(2) Scrapling 同步调用与 AI4TALENT 异步体系的衔接。

```python
# backend/app/domains/lab_web/services/collectors/scrapling_fetcher.py
class ScraplingFetcher:
    """Scrapling Fetcher 的封装层。

    - 把 Scrapling 的同步抓取包到 anyio.to_thread.run_sync 里，避免阻塞事件循环。
    - 代理/超时/SSL 等配置从 HttpClientFactory 读取，保持与企业内网代理配置一致。
    - 对外只暴露 fetch(url) -> Scrapling Selector（解析后的页面）。
    """

    def __init__(self, fetch_mode: str = "static") -> None:
        self.fetch_mode = fetch_mode

    async def fetch(self, url: str) -> Any:
        """抓取页面并返回 Scrapling Selector 对象供钩子解析。"""
        # 从 HttpClientFactory 读取代理、UA、超时、SSL 等统一配置
        # 用 anyio.to_thread.run_sync 包装 Scrapling 同步调用
        ...
```

**架构例外说明**：Scrapling 的 `Fetcher` 内部用 `httpx`/`requests`，而 AI4TALENT 铁律要求所有出站请求经 `HttpClientFactory`。处理策略：`ScraplingFetcher` **从 `HttpClientFactory` 读取代理、UA、超时、SSL 等配置参数**（保持配置来源单一），传给 Scrapling 的 `Fetcher` 使用。配置层面统一（企业内网代理不漏配），但实际抓取由 Scrapling 完成（官网爬虫需要 Scrapling 的反爬/自适应能力，这是引入 Scrapling 的初衷）。属于**已知的、有正当理由的架构例外**，在 `AGENTS.md` 记录（参照 `github_client.py` import httpx 的既有例外处理方式）。

**备选方案**（如需严格化）：完全不用 Scrapling 的 `Fetcher`，只用它的 `Selector`（纯 HTML 解析，无网络），抓取动作改用 `HttpClientFactory` 造的 `httpx.AsyncClient`。代价是失去 Scrapling 的反爬能力，退化成普通 httpx 抓取。当前按"配置统一、抓取用 Scrapling"设计；如实施时发现架构检查脚本（`check_architecture.py`）不放过 Scrapling 的内部 httpx，则降级到备选方案（只用 Selector）。

---

## 6. 标准化规则

### 6.1 角色映射：细粒度原文 + 粗粒度枚举双轨

官网原始头衔是细粒度原文（如 `Assistant Professor`、`PhD Candidate`），AI4TALENT 现有 `RoleType` 是粗粒度四档（`PROFESSOR/STUDENT/GRADUATE/UNKNOWN`）。采用双轨：

| 字段 | 位置 | 粒度 | 用途 |
|------|------|------|------|
| `title_raw` | `lw_raw_person` | 原文 | 完整保留官网头衔，回溯用 |
| `current_title` | `core_talent` | 原文 | 前端展示、精细筛选 |
| `role_type` | `core_talent` | 四档枚举 | 粗筛、统计、与学术人才统一口径 |
| `role_confidence` | `core_talent` | 0.0–1.0 | 标注本次映射的确定性 |

官网采集的角色分类置信度高（直接来自页面声明，非推断），`role_confidence` 通常 0.9–1.0。

### 6.2 角色映射规则（`constants/role_mapping.py`）

基于关键词子串匹配的规则引擎。返回 `(RoleType, confidence)`。

```python
ROLE_RULES: list[tuple[list[str], RoleType, float]] = [
    # Professor 系列 —— 明确声明教职
    (["professor", "lecturer", "faculty"], RoleType.PROFESSOR, 0.95),
    # 研究员系列（非学生、非教职的独立研究者）
    (["research scientist", "researcher", "research engineer",
      "staff scientist", "principal investigator", "pi"], RoleType.PROFESSOR, 0.85),
    # 博士后 —— 按 AI4TALENT 口径归 GRADUATE（已毕业的早期研究者）
    (["postdoc", "postdoctoral", "post-doc"], RoleType.GRADUATE, 0.9),
    # 学生系列 —— 明确在读
    (["phd", "ph.d", "doctoral", "candidate",
      "master", "ms student", "m.s.", "meng",
      "undergraduate", "ugrad", "bachelor"],
     RoleType.STUDENT, 0.95),
    # 访问学者 —— 归 UNKNOWN，保留原文
    (["visiting", "visiting scholar", "visiting student"], RoleType.UNKNOWN, 0.6),
]


def map_role_type(title_raw: str | None) -> tuple[RoleType, float]:
    """标题 → 标准角色 + 置信度。无匹配时返回 (UNKNOWN, 0.0)。"""
    if not title_raw:
        return RoleType.UNKNOWN, 0.0
    text = title_raw.lower()
    for keywords, role, conf in ROLE_RULES:
        if any(kw in text for kw in keywords):
            return role, conf
    return RoleType.UNKNOWN, 0.0
```

设计要点：
- 子串匹配（非精确），应对官网头衔写法差异（`Assistant Professor of Computer Science` / `Assoc. Prof.`）。
- 规则按特异性排序。
- `title_raw` 始终保留，规则只影响 `role_type` 枚举值，不丢信息。
- 博后归 `GRADUATE`：对齐 OpenAlex 口径（已毕业的早期研究者）。

### 6.3 邮箱反混淆（`normalize_email`）

覆盖学术官网主流混淆写法：

| 原始写法 | 标准化结果 |
|---------|-----------|
| `john [at] cs [dot] stanford [dot] edu` | `john@cs.stanford.edu` |
| `john(ät)cs.stanford.edu` | `john@cs.stanford.edu` |
| `john [AT] CS [DOT] STANFORD [DOT] EDU` | `john@cs.stanford.edu` |
| `<script>document.write('john'+'@'+'cs...')</script>` | `None`，原文存 `raw_data`（JS 渲染邮箱第一版不解析） |
| 标准 `john@cs.stanford.edu` | 原样返回 |

反混淆失败时返回 `None`，原始字符串仍存进 `lw_raw_person.raw_data`。

### 6.4 姓名标准化（`normalize_name`）

- 合并连续空白、去除首尾空白。
- 不强制改大小写（`Title Case` 在中英混合时不可靠），保留原文形式。
- 中英混合姓名原样保留，`name_en` 在能识别拉丁字母部分时填充。

### 6.5 content_hash 计算

```
content_hash = sha256(
    lab_code + "|" +
    normalized_name + "|" +
    (title_raw or "") + "|" +
    (normalized_email or "") + "|" +
    (homepage_url or "")
)
```

- 用标准化后字段参与哈希，保证同一人跨次采集哈希稳定。
- `source_url` 不参与（同人官网 URL 可能变，但人不变）。
- `avatar_url` 不参与（CDN 路径常变）。
- 哈希用作 `core_talent.source_record_id`（unique），保证同一官网人物在服务层只有一条记录。

---

## 7. 编排与同步服务

### 7.1 服务职责划分

```
lw_collection_service.py    —— 对外门面，编排"一次完整采集"
lw_person_service.py        —— 对内，负责 raw → core_talent 同步
LWRepository                —— 数据访问层，封装 lw_* 三张表的读写
```

对齐 `open_source` 域分层。Endpoint 只能调 Service（Endpoint 分层铁律）。

### 7.2 `LWCollectionService`（采集编排）

```python
class LWCollectionService:
    """官网人才采集编排服务。"""

    async def start_collection(self, lab_id: int, created_by: int | None = None) -> int:
        """创建并启动一次采集任务，返回 task_id。
        - 校验 lab 存在、is_active、collector_class 已注册
        - 在 lw_collect_task 插入 pending 记录
        - 异步触发 _run_collection（不阻塞 API 响应）
        """

    async def get_task_status(self, task_id: int) -> TaskStatusDTO | None:
        """查询任务进度（供前端轮询）。"""

    async def cancel_collection(self, task_id: int) -> bool:
        """请求取消运行中的任务（设置 cancelled Event）。"""

    async def list_labs(self) -> list[LabDTO]:
        """列出实验室注册表（前端选择采集目标）。"""

    async def _run_collection(self, task_id: int, lab_id: int) -> None:
        """实际采集流程（后台执行）：
        1. 加载 lab → 实例化对应 collector_class（动态导入）
        2. 实例化 ScraplingFetcher（按 lab.fetch_mode）
        3. 构造 CollectContext
        4. await collector.collect(ctx)   # 基类固化流程在此执行
        5. 捕获异常 → 任务标记 failed + error_message
        6. 正常结束 → 任务标记 success + 更新 lab.last_collected_at
        """
```

**采集器动态加载**：`lw_lab_registry.collector_class` 存字符串路径。`_run_collection` 用 `importlib` 动态导入并实例化。加实验室 = 加一个 collector 文件 + 改一行注册表数据。`collector_class=null` 调用 `start_collection` 时返回明确错误。

**任务异步触发**：参照 `OSCollectionService` 既有模式。API 调用 `start_collection` 立即返回 `task_id`，前端轮询 `get_task_status`。任务失败不抛异常到 API，只记进 `error_message`。

### 7.3 `LWPersonService`（raw → core_talent 同步）

```python
class LWPersonService:
    """官网原始人才数据 → core_talent 服务层同步。"""

    async def sync_to_core_talent(
        self, raw_persons: list[LWRawPerson], lab: LWLabRegistry
    ) -> SyncResult:
        """批量同步原始人员到 core_talent。
        策略：基于 content_hash 作为 source_record_id 做 upsert。
        - 已存在（source_type=lab_web 且 source_record_id 匹配）→ 更新可变字段
        - 不存在 → 新增
        - 事务批量提交（SYNC_COMMIT_BATCH_SIZE 控制批次）
        """
```

字段映射见 §4.5。**upsert 冲突处理**：只 upsert `source_type='lab_web'` 的记录，通过 `WHERE source_type='lab_web'` 限定查询范围。

### 7.4 数据访问层 `LWRepository`

```python
class LWRepository:
    """lab_web 域数据访问层，封装三张 lw_* 表的读写。"""

    async def get_lab(self, lab_id: int) -> LWLabRegistry | None: ...
    async def list_labs(self, only_active: bool = False) -> list[LWLabRegistry]: ...
    async def get_lab_by_code(self, lab_code: str) -> LWLabRegistry | None: ...

    async def create_task(self, **kwargs) -> LWCollectTask: ...
    async def update_task(self, task_id: int, **kwargs) -> None: ...
    async def get_task(self, task_id: int) -> LWCollectTask | None: ...

    async def upsert_raw_persons(
        self, lab_id: int, drafts: list[RawPersonDraft], task_id: int
    ) -> list[LWRawPerson]:
        """批量写入 raw 层。计算 content_hash，重复 hash 跳过（同次采集内）。"""

    async def get_raw_persons_by_task(self, task_id: int) -> list[LWRawPerson]: ...
```

所有 DB 操作走注入的 `AsyncSession`（`Depends(get_async_session)`），不直接 `AsyncSessionLocal()`（Endpoint 分层铁律）。

### 7.5 API 层（`api/collection.py`）

```python
r = APIRouter(prefix="/lab-web", tags=["lab-web"])

@r.get("/labs")                        # 列实验室 → service.list_labs
@r.post("/labs/{lab_id}/collect")      # 触发采集 → service.start_collection
@r.get("/tasks/{task_id}")             # 查任务状态 → service.get_task_status
@r.post("/tasks/{task_id}/cancel")     # 取消任务 → service.cancel_collection
@r.get("/tasks")                       # 任务列表
```

注册到 `app/api_router.py`（一行改动）。Endpoint 仅依赖 `LWCollectionService`，不碰 Repository/Collector。

---

## 8. 合规护栏

| 护栏 | 实现 | 位置 |
|------|------|------|
| robots.txt 检查 | 采集前请求 `/robots.txt`，若 `Disallow` 覆盖目标路径 → 任务 `failed`，不抓取 | `BaseLabCollector.collect()` step 2 |
| 限速 | 同一实验室两次请求间隔 ≥ `request_delay`（默认 1s），单实验室内串行 | `ScraplingFetcher` + `BaseLabCollector` |
| UA 标识 | 诚实 UA（如 `AI4TALENT-LabWebCollector/1.0`），不伪装浏览器 | `ScraplingFetcher` 配置 |
| 并发上限 | 同时进行的采集任务数受限（配置项，默认 2），避免压垮目标站 | `LWCollectionService` 信号量 |
| 无 StealthyFetcher | 不用 Scrapling `StealthyFetcher`（主动反爬绕过）。遇 Cloudflare 类保护直接 `failed` | 架构约束 |
| 超时与重试 | 单页超时 30s（复用 `HTTP_TIMEOUT_DEFAULT`），最多重试 2 次（指数退避），超出标记该页失败 | `ScraplingFetcher` |
| 数据最小化 | 只采集 People 页公开人员信息，不抓取个人详情页的私人内容（如电话） | `extract_person` 钩子约束 |

明确不做：不绕验证码、不模拟登录、不对抗 WAF。LinkedIn 留后续独立模块。

---

## 9. 测试策略

对齐 AI4TALENT 测试规范。**所有单元/集成测试不真实请求 `ai.stanford.edu`**。

| 测试类型 | 内容 | 标记 |
|---------|------|------|
| 单元 | `role_mapping`（各头衔→角色）、`normalize_email`（各混淆写法）、`normalize_name`、`content_hash` 稳定性 | `unit` |
| 单元 | `BaseLabCollector` 用 fake fetcher + fake response 跑通 10 步主流程，验证钩子被正确调用、raw 层写入、task 状态流转 | `unit` |
| 集成 | `LWPersonService.sync_to_core_talent`：raw → core_talent upsert，验证同 content_hash 不重复、不同 hash 各一条、`source_type=lab_web` 隔离不污染 openalex 记录 | `integration` |
| 集成 | `LWRepository` 三张表 CRUD（用测试库 `talent_db_test`） | `integration` |
| E2E（可选） | 用本地 httpbin fixture 模拟 SAIL 页面结构，跑完整 `start_collection` → 数据落库 | `slow` |

**网络隔离**：SAIL 适配器测试用录制的 HTML 快照（`tests/fixtures/lab_web/stanford_sail_people.html`）喂给 `Selector`。真实网络抓取只在手动验证或 `slow` 标记的冒烟测试里做。

**测试数据库**：复用 `talent_db_test`，三张 `lw_*` 表随 Alembic 迁移建出，`conftest.py` 的 `DROP/TRUNCATE` 机制自动覆盖新表。

---

## 10. 成功标准（验收）

第一版 spec 完成 = 全部满足：

1. ✅ Alembic 迁移建出 `lw_lab_registry` / `lw_raw_person` / `lw_collect_task` 三张表，注册表预置 ~10 个实验室（SAIL 的 `collector_class` 填实，其余 null）
2. ✅ `SourceType.LAB_WEB` 枚举加入，模型注册到 `model_registry.py`
3. ✅ 运行 `start_collection(lab_id=<SAIL>)`，能从 Stanford SAIL People 页抓取全部人员，写入 `lw_raw_person`
4. ✅ 同步到 `core_talent`（`source_type='lab_web'`），角色分类（`role_type`）正确映射，`source_record_id` 唯一去重
5. ✅ 重复运行同一实验室采集，`core_talent` 不产生重复记录（upsert 生效）
6. ✅ 任务状态可查询（pending → running → success/failed），进度百分比更新
7. ✅ 单元 + 集成测试通过，覆盖角色映射、邮箱反混淆、upsert 去重、主流程
8. ✅ `ruff` + `black` + `mypy gate` + `check_architecture.py` 全部通过（CI 绿）
9. ✅ robots.txt 被禁的路径能被正确拦截（构造测试用例验证）

---

## 11. 风险与已知约束

| 风险 | 影响 | 缓解 |
|------|------|------|
| Scrapling 与 HttpClientFactory 铁律的张力 | 架构合规 | 已知架构例外，`ScraplingFetcher` 从 Factory 读配置保持统一，在 `AGENTS.md` 记录。备选：只用 Scrapling 的 `Selector`，抓取走 httpx |
| SAIL 页面结构变更 | 适配器失效 | raw 层保留 `raw_data` 快照可回溯；钩子集中在单文件易改；`title_raw`/`name_raw` 原文保留便于诊断 |
| SAIL 分页/JS 渲染 | 抓不全 | `fetch_mode` 字段可切 `dynamic`（Scrapling DynamicFetcher）；分页钩子 `get_next_page_url` 已预留 |
| 跨源同人重复（官网+OpenAlex） | 同人两条 core_talent | 本 spec 明确不解决，留 `unified_person_id` 后续。`source_type` 区分 |
| 邮箱 JS 渲染 | 漏邮箱 | 原文存 raw_data，`fetch_mode=dynamic` 时浏览器渲染可拿到；静态模式记 None 不阻塞 |
| Scrapling 依赖体积（playwright 等） | 安装重 | 仅在 `fetch_mode=dynamic` 的实验室需要 playwright；`lab_web` 域按需导入，base 安装不带 |
| Windows + Scrapling + asyncpg 共存 | 环境冲突 | Scrapling 只在 collectors 子层用到，隔离在 `services/collectors/`，不污染 core |

---

## 12. 依赖新增

`backend/pyproject.toml`：

```toml
[project]
dependencies = [
    # ... existing ...
    "scrapling>=0.4.9",   # 官网 People 页抓取与解析
]
```

Scrapling 的 fetcher 依赖（playwright/patchright）作为可选 extra，仅在 `fetch_mode=dynamic` 时需要。第一版 SAIL 若是静态页则 base scrapling 即可。

---

## 附录 A：预置实验室清单（第一版）

7–8 国外 + 1–2 国内。仅 SAIL 填 `collector_class`，其余 null。

| lab_code | lab_name | institution | country | collector_class |
|----------|----------|-------------|---------|-----------------|
| `stanford_sail` | Stanford AI Lab | Stanford University | US | `labs.stanford_sail.StanfordSailCollector` |
| `mit_csail` | MIT CSAIL | MIT | US | null |
| `deepmind` | Google DeepMind | Google | UK | null |
| `fair` | FAIR | Meta | US | null |
| `openai` | OpenAI | OpenAI | US | null |
| `anthropic` | Anthropic | Anthropic | US | null |
| `msr` | Microsoft Research | Microsoft | US | null |
| `bair` | Berkeley AI Research | UC Berkeley | US | null |
| `baai` | 北京智源人工智能研究院 | BAAI | CN | null |
| `tsinghua_air` | 清华大学人工智能研究院 | Tsinghua University | CN | null |

> 实际预置清单以实施时核实为准；此表为示意。
