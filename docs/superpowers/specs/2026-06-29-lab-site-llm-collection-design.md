# 设计文档：实验室站点 LLM 采集（lab_web_site v2）

- **状态**：草案，待用户复核
- **日期**：2026-06-29
- **目标项目**：AI4TALENT（`D:\AI\AI4TALENT-lab-web`，worktree on `feature/lab-web-talent-collection`）
- **范围标识**：lab_web 域第二期 —— LLM 驱动的实验室站点 People 页采集
- **前置 spec**：`2026-06-28-lab-web-talent-collection-design.md`（v1，代码选择器采集 SAIL /faculty/）
- **调研依据**：`docs/superpowers/research/2026-06-29-sail-data-source-research.md`

---

## 1. 背景与目标

### 1.1 上下文

v1（已实现）用代码 CSS 选择器采集 SAIL `/faculty/`，拿到 63 位教授，但**列表页无头衔、无邮箱、无学生**。调研（2026-06-29）证实：

- 博士学生/博后**不在 SAIL 主站**，分布在 `/research-groups/` 链接的 22 个独立实验室站点。
- 这些实验室站点普遍有 **People 页 + 角色分区**（Faculty / PhD Students / Postdocs / Staff / Alumni），是获取学生 + 角色标签的有效来源。
- 22 个站点**结构各异**（NLP 用 `div.team-member`、snap 用 `<tr>`/`<li>`、Ermon 用 `<li>`、ML Group 用 SPA 锚点），手写 CSS 选择器的代码流程模式在这种异构规模下是反模式。

### 1.2 v2 的核心转变

从 v1 的"每站一个选择器子类"转变为**"LLM 驱动解析"**：抓取层仍用代码（合规可控），解析层把 HTML 喂给项目已有的 LLM 网关，让 LLM 输出结构化人员 JSON。新增站点从"写代码"变成"加一行 config"。

### 1.3 用途

承接 v1 的双目标（研究分析 + 招聘线索），补齐 v1 的根本缺口：
- **角色分类**：通过实验室站点的角色分区，真正区分教授/博士学生/博后（v1 全是 UNKNOWN）。
- **学生覆盖**：拿到 v1 完全没有的博士学生数据。

---

## 2. 总体方案

### 2.1 关键架构决策（已逐项与用户确认）

| 决策 | 选择 | 理由 |
|------|------|------|
| 与 v1 数据关系 | 独立数据源 `source_type='lab_web_site'` | 不污染 v1 的 `lab_web`（/faculty/ 教授），跨源合并留未来 |
| 角色建模 | 复用 `core_talent.role_type` 四档 + 原始标签进 `extra_data.role_section_raw` | 零侵入既有表 |
| 解析层 | **LLM 驱动**（项目 LLM 网关） | 异构站点用代码选择器是反模式 |
| 调用时机 | 首次 LLM 解析 + HTML-hash 缓存复用 | 数据低频变化，省成本，缓解 LLM 随机性 |
| 质量保障 | JSON schema 校验 + 重试 + `needs_review` | 防 LLM 脏数据灌入 core_talent |

### 2.2 v2 范围（本 spec 覆盖）

- `BaseLabSiteCollector`（LLM 解析管线，固化"抓取→缓存判断→LLM解析→校验→入库"流程）
- LLM 提示词 + 人员 JSON schema 校验（Pydantic）
- HTML 预处理（去 script/style/冗余，压缩到合理大小）
- `lw_site_config`（站点注册表）+ `lw_site_raw_page`（HTML 快照 + 解析结果 + 缓存）两张新表
- `role_section → role_type` 映射规则
- 3 个实验室站点适配（NLP Group / snap / Ermon，已探测确认均有角色分区）
- `LWSiteCollectionService` 编排（复用 lw_collect_task + cancel-watcher）
- 5 个 API endpoint
- 单元 + 集成测试（LLM 全程 mock）

### 2.3 明确不在 v2 范围

- 其余 19 个实验室站点（架构预留，加 config 行即可）
- 邮箱获取（站点普遍隐藏，留 v3 评估 JS 渲染）
- 跨源实体合并（`unified_person_id`，留未来）
- 教授-学生导师关系建模
- 前端审核界面（`needs_review` 数据暂通过 SQL/脚本处理）
- 真实 LLM 验收的自动化（手动 `slow` 标记，不入 CI）

---

## 3. 数据模型

### 3.1 新增表 `lw_site_config`（站点注册表）

轻量配置表，类似 v1 的 `lw_lab_registry`。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `site_id` | Integer | PK, autoincrement | 主键 |
| `site_code` | String(50) | unique, not null, index | 站点码，如 `stanford_nlp_group` |
| `site_name` | String(255) | not null | 显示名 |
| `parent_lab_code` | String(50) | not null | 所属实验室码（关联 lw_lab_registry.lab_code），如 `stanford_sail` |
| `people_url` | String(500) | not null | People 页 URL |
| `fetch_mode` | String(20) | not null, default 'static' | 预留 JS 渲染分支（v2 第一版全 static） |
| `is_active` | Boolean | not null, default True | 是否启用 |
| `last_collected_at` | DateTime | nullable | 最近采集时间 |
| `notes` | Text | nullable | 备注 |
| + `TimestampMixin` | | | created_at/updated_at |

**无 collector_class 字段**——v2 所有站点共用 `BaseLabSiteCollector`，靠 config 参数实例化，不需每站一个子类。

### 3.2 新增表 `lw_site_raw_page`（HTML 快照 + 解析结果 + 缓存）

v2 的核心新表，承载缓存逻辑。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `page_id` | Integer | PK, autoincrement | 主键 |
| `site_code` | String(50) | not null, index | 关联 lw_site_config.site_code |
| `people_url` | String(500) | not null | 抓取的 URL |
| `html_content` | Text | not null | 原始 HTML 快照 |
| `html_hash` | String(64) | not null, index | HTML 内容 SHA-256（缓存键） |
| `parsed_persons` | JSON | nullable | LLM 解析出的人员结构化数据 |
| `parse_status` | String(20) | not null, default 'pending', index | `pending`/`parsed`/`needs_review`/`failed` |
| `parse_error` | Text | nullable | 解析失败/校验失败原因 |
| `llm_model` | String(100) | nullable | 用的 LLM 模型名 |
| `llm_tokens_used` | Integer | nullable | LLM token 消耗（成本监控） |
| `fetched_at` | DateTime | not null, default now | HTML 抓取时间 |
| `parsed_at` | DateTime | nullable | LLM 解析时间 |
| + `created_at` | | | |

**缓存键**：`(site_code, html_hash)`。采集时若存在 `parse_status='parsed'` 的同键记录，复用其 `parsed_persons`，不调 LLM。raw 层只追加（同 v1 设计），保留历史快照。

### 3.3 复用既有表

- **`lw_collect_task`**：任务管理（v1 已建）。v2 复用此表，通过 `config_json` 里的 `source` 字段（`'lab_web'` vs `'lab_web_site'`）和 `site_code` 区分。schema 不变。
- **`lw_raw_person`**：原始人员层（v1 已建）。v2 也写入此表，`lab_id` 字段存 `site_id`（复用外键或存 site_code 到 raw_data）。为避免与 v1 的 lab_id（指向 lw_lab_registry）语义混淆，v2 在 `lw_raw_person.raw_data` 里额外存 `site_code`、`source_type='lab_web_site'`。
- **`core_talent`**：服务层（v1 已用）。v2 写入 `source_type='lab_web_site'`，`source_record_id` = content_hash（基于 site_code + name + role_section + homepage），`role_type` 四档映射，`extra_data.role_section_raw` 存原始标签。

### 3.4 与 v1 的隔离

`source_type` 是硬隔离边界：
- v1（/faculty/ 教授）：`source_type='lab_web'`
- v2（实验室站点）：`source_type='lab_web_site'`
- upsert 时 `WHERE source_type='lab_web_site'` 限定，绝不碰 v1 或 openalex 记录。

---

## 4. 采集流程（`BaseLabSiteCollector`）

### 4.1 主流程（基类固化，子类不碰）

```
collect(ctx) 主流程
  │
  ├─ 1. 前置校验：site 配置存在、is_active、people_url
  ├─ 2. 合规护栏：robots.txt 检查 people_url（复用 v1 ScraplingFetcher.is_allowed_by_robots）
  ├─ 3. 抓取 HTML：ScraplingFetcher.fetch（复用 v1 抓取层）
  ├─ 4. 计算 html_hash = sha256(html_content)
  ├─ 5. 缓存判断：查 lw_site_raw_page 是否有 (site_code, html_hash, parse_status='parsed')
  │     └─ 命中 → 直接用 parsed_persons，跳到 step 8（force_reparse=False 时）
  ├─ 6. HTML 预处理：Selector 提取 body 文本，去 script/style/冗余属性，压缩
  ├─ 7. LLM 解析 + 校验（见 §4.2）
  ├─ 8. 写入 lw_site_raw_page（HTML 快照 + parsed_persons + html_hash + parse_status）
  ├─ 9. 转换为 RawPersonDraft 列表（带 role_section_raw），写入 lw_raw_person
  └─ 10. 同步 core_talent（source_type='lab_web_site'，role_type 映射 + extra_data）
```

步骤 1-5、8-10 是**固定流程**（基类实现），步骤 6-7 是 **LLM + 校验**（基类内置）。**子类零代码**——仅作为配置载体（或完全不用子类，config 表 + 通用实例化）。

### 4.2 LLM 解析 + 校验（step 7）

```
7a. 调 LLM 网关，提示词 + 预处理后的 HTML → LLM 返回文本
7b. 解析 LLM 输出为 list[ParsedPerson]（Pydantic 校验）
    └─ 失败 → 重试一次（7a 再调）
       └─ 仍失败 → parse_status='needs_review'，parse_error 记原始输出，结束（不进 core_talent）
7c. 校验通过但人员数为 0 → 也标记 needs_review（People 页至少该有人）
7d. 校验通过 → parsed_persons 写入，parse_status='parsed'
```

### 4.3 LLM 提示词

复用项目 LLM 网关（`domains/shared/services/llm/`，支持 DeepSeek/OpenAI/智谱）。系统提示词 + 用户消息（HTML）：

```
你是一个网页数据抽取助手。下面是一个大学实验室的 People 页面 HTML。
请抽取页面中的所有人员，按他们在页面中所属的角色分区分类。

要求：
1. 只抽取真实人员（跳过导航、页脚、装饰性文字）。
2. 每个人员必须有 name（姓名）。
3. role_section 是该人员在页面中所属分区的原始标签（如 "Faculty"、"PhD Students"、
   "Postdocs"、"Staff"、"Alumni"）；如果页面无分区，填 "Unknown"。
4. 尽可能提取 homepage（个人主页 URL）和 department（院系/专业，如有）。
5. 跳过已毕业/离校的 Alumni（除非分区明确标注 Alumni，则 role_section 填 "Alumni"）。

输出严格的 JSON 数组，不要任何额外文字：
[
  {"name": "...", "role_section": "...", "homepage": "...", "department": "..."},
  ...
]

=== HTML 开始 ===
{html}
=== HTML 结束 ===
```

### 4.4 人员 JSON schema（Pydantic）

```python
class ParsedPerson(BaseModel):
    name: str                        # 必填，非空
    role_section: str = "Unknown"    # 原始分区标签
    homepage: str | None = None      # 若提供，必须是合法 URL
    department: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()

    @field_validator("homepage")
    @classmethod
    def valid_url_if_present(cls, v: str | None) -> str | None:
        if v is None:
            return None
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"invalid homepage URL: {v}")
        return v
```

### 4.5 HTML 预处理（step 6）

原始 HTML 可能很大（NLP Group 184KB），直接喂 LLM 既贵又可能超 token。预处理步骤：

1. 用 Scrapling `Selector(html)` 解析
2. 移除 `<script>`、`<style>`、`<nav>`、`<footer>`、`<header>` 节点
3. 提取 `<body>` 的文本内容 + 保留人员相关结构（如 `div.team-member`、`<li>`、`<tr>` 的层级）
4. 压缩冗余空白
5. 若仍超阈值（如 50KB），截断并记 warning（极端情况）

预处理的目的是给 LLM 一个干净、紧凑、聚焦人员的输入，不是钩子——是基类的固定步骤。

### 4.6 role_section → role_type 映射（step 10 用）

```python
# constants/site_role_mapping.py
SITE_ROLE_RULES: list[tuple[list[str], RoleType, float]] = [
    (["faculty", "professor", "pi", "principal investigator"], RoleType.PROFESSOR, 1.0),
    (["postdoc", "postdoctoral", "post-doc"], RoleType.GRADUATE, 1.0),
    (["phd", "ph.d", "doctoral", "student", "graduate student"], RoleType.STUDENT, 1.0),
    (["research scientist", "research engineer", "staff scientist", "staff"], RoleType.PROFESSOR, 0.9),
    (["alumni", "alumnus", "alumna"], RoleType.UNKNOWN, 1.0),  # 已离开
    (["visiting"], RoleType.UNKNOWN, 0.6),
]

def map_site_role(role_section: str | None) -> tuple[RoleType, float]:
    """角色分区标签 → 四档 role_type。置信度普遍 1.0（站点明确声明）。"""
    if not role_section:
        return RoleType.UNKNOWN, 0.0
    text = role_section.lower()
    for keywords, role, conf in SITE_ROLE_RULES:
        if any(kw in text for kw in keywords):
            return role, conf
    return RoleType.UNKNOWN, 0.0
```

置信度给 1.0（站点明确分区声明，比 v1 的标题子串推断可靠得多）。原始 `role_section` 存进 `core_talent.extra_data['role_section_raw']`。

---

## 5. 编排服务与 API

### 5.1 `LWSiteCollectionService`（采集编排）

与 v1 的 `LWCollectionService` 平行，复刻任务管理 + 后台执行 + cancel-watcher。

```python
class LWSiteCollectionService:
    async def list_sites(self, only_active: bool = False) -> list[LWSiteConfig]: ...
    async def start_collection(
        self, site_code: str, force_reparse: bool = False, created_by: int | None = None
    ) -> int: ...
    async def get_task_status(self, task_id: int) -> LWCollectTask | None: ...
    async def cancel_collection(self, task_id: int) -> bool: ...
    async def get_review_items(self, site_code: str) -> list[LWSiteRawPage]: ...
```

**站点实例化**：`start_collection(site_code)` 从 `lw_site_config` 查配置 → 用配置参数实例化 `BaseLabSiteCollector`（无子类）→ 后台跑 `collect`。`force_reparse=True` 时基类 step 5 跳过缓存判断，强制重新 LLM 解析。

### 5.2 API（`api/site_collection.py`）

前缀 `/lab-web-sites`，与 v1 的 `/lab-web` 平行：

```python
@router.get("/sites")                              # 列站点
@router.post("/sites/{site_code}/collect")         # 触发采集（query: force_reparse=false）
@router.get("/tasks/{task_id}")                    # 查任务状态（复用 lw_collect_task）
@router.post("/tasks/{task_id}/cancel")            # 取消
@router.get("/sites/{site_code}/review")           # 查看 needs_review 的解析结果
```

注册到 `app/api_router.py`（一行）。

### 5.3 枚举扩展

`SourceType` 新增：

```python
class SourceType(str, enum.Enum):
    OPENALEX = "openalex"
    MANUAL = "manual"
    IMPORT = "import"
    LAB_WEB = "lab_web"          # v1
    LAB_WEB_SITE = "lab_web_site"  # v2 新增
```

---

## 6. 错误处理与可观测

| 场景 | 处理 |
|------|------|
| LLM 网关不可用/超时 | 任务 `failed`，error_message 记录；HTML 已抓取存 raw_page（parse_status='pending'），重试可复用 HTML |
| LLM 输出非 JSON / schema 失败 | 重试一次，仍失败 → parse_status='needs_review'，任务 `partial` |
| LLM 返回 0 人员 | needs_review（避免空数据误判） |
| robots.txt 禁止 | 任务 `failed`，不抓取（复用 v1 _guard_robots_txt） |
| HTTP 403/超时 | 任务 `failed`，记录状态码 |
| 单站点失败 | 不影响其他站点（独立任务） |
| LLM 成本 | config_json 记 `llm_tokens_used`，可监控 |

**任务状态扩展**：v2 在 `lw_collect_task.config_json` 里存 `{source: 'lab_web_site', site_code, force_reparse, llm_tokens_used}`，区分 v1/v2 任务。

---

## 7. 测试策略

**LLM 调用全程 mock，绝不在测试里真实调 LLM API。**

| 类型 | 内容 | LLM |
|------|------|-----|
| 单元 | HTML 预处理（去 script/style、压缩、保留结构） | 不涉及 |
| 单元 | JSON schema 校验（合法/非法/空数组/字段缺失/URL 非法） | mock 返回固定 JSON |
| 单元 | role_section → role_type 映射 | 不涉及 |
| 单元 | 缓存命中/未命中（html_hash 对比） | mock repo + LLM |
| 单元 | BaseLabSiteCollector 主流程（mock fetcher + mock LLM + fake repo） | mock 全程 |
| 集成 | raw → core_talent 同步（source_type=lab_web_site 隔离，不碰 v1/openalex） | mock LLM 返回固定人员 |
| 集成 | Repository 三表 CRUD（lw_site_config / lw_site_raw_page / lw_collect_task） | 不涉及 |
| 手动（slow） | 真实 LLM 抓 NLP Group，人工核对人员/角色 | **真实 LLM**，`@pytest.mark.slow`，不入 CI |

**网络隔离**：HTML 抓取用录制快照 fixture（`tests/fixtures/lab_web/nlp_group_people.html` 等，截取片段），LLM 用 mock 返回预录 JSON。

---

## 8. 预置站点（3 个，已探测确认）

基于 2026-06-29 探测，3 个站点均有清晰角色分区标记：

| site_code | site_name | parent_lab_code | people_url | 探测结果 |
|-----------|-----------|-----------------|------------|---------|
| `stanford_nlp_group` | Stanford NLP Group | stanford_sail | `https://nlp.stanford.edu/people/` | 470 team-member，Faculty/PhD Students/Postdocs/Staff/Alumni 分区 |
| `stanford_snap` | SNAP Group | stanford_sail | `http://snap.stanford.edu/people.html` | Faculty/PhD Students/Postdocs/Staff/Alumni/Visiting 分区，46 tr + 78 li |
| `stanford_ermon` | Ermon Lab | stanford_sail | `https://cs.stanford.edu/~ermon/website/people.html` | Faculty/Ph.D. Students/Postdocs/Alumni/Visiting 分区 |

3 个站点结构差异足够（team-member / tr+li / li），能充分验证 LLM 解析的通用性。

---

## 9. 成功标准（验收）

v2 完成 = 全部满足：

1. ✅ `lw_site_config` + `lw_site_raw_page` 两张表建出，预置 3 个站点
2. ✅ `SourceType.LAB_WEB_SITE` 枚举加入，模型注册到 model_registry.py
3. ✅ `BaseLabSiteCollector` LLM 解析管线跑通（mock 测试覆盖全流程）
4. ✅ 缓存逻辑工作：同 html_hash 不重复调 LLM；force_reparse 强制重解析
5. ✅ schema 校验拦截非法 LLM 输出（重试 + needs_review）
6. ✅ 人员写入 lw_raw_person + core_talent（source_type='lab_web_site'），role_type 正确映射
7. ✅ 跨源隔离：v2 数据不碰 v1（lab_web）/openalex 记录
8. ✅ 手动验收：真实 LLM 抓 NLP Group，能拿到带角色（PhD Students）的学生数据
9. ✅ ruff + black + mypy gate + check_architecture 全绿
10. ✅ 不破坏 v1（v1 的 43 个测试仍通过）

---

## 10. 风险与缓解

| 风险 | 缓解 |
|------|------|
| LLM 解析准确率不达预期 | schema 校验 + needs_review 兜底；手动验收统计准确率，低于阈值调提示词 |
| LLM 成本超预期 | HTML 预处理 + 缓存复用；config_json 记 token 用量可监控 |
| 大页面超 LLM token 限制 | HTML 预处理压缩；极端截断 + warning |
| LLM 网关测试环境不可用 | 全程 mock，不依赖真实 LLM |
| 3 站点结构差异超 LLM 适应力 | 手动验收逐站验证；不适配标记 needs_review |
| LLM 输出随机性（同页两次解析略异） | 缓存复用——同 html_hash 只解析一次，结果稳定 |

---

## 11. 目录结构（新增）

```
backend/app/domains/lab_web/
├── constants/
│   └── site_role_mapping.py          # role_section → role_type 映射
├── models/
│   └── lab_web_site.py               # LWSiteConfig, LWSiteRawPage
├── schemas/
│   └── lab_web_site.py               # ParsedPerson, SiteBrief, SiteCollectResponse 等 DTO
├── services/
│   ├── lw_site_collection_service.py # 编排
│   ├── lw_site_person_service.py     # raw → core_talent 同步（source_type=lab_web_site）
│   └── collectors/
│       ├── base_site_collector.py    # BaseLabSiteCollector（LLM 管线）
│       └── llm_parser.py             # LLM 调用 + 提示词 + schema 校验
├── api/
│   └── site_collection.py            # 5 个 endpoint
└── ...（v1 文件不变）

backend/migrations/versions/051_add_lab_web_site.py   # 两张新表 + 种子
```

---

## 12. 依赖

无新外部依赖——复用项目已有：
- LLM 网关（`domains/shared/services/llm/`，DeepSeek/OpenAI/智谱）
- HttpClientFactory（抓取层）
- Scrapling Selector（HTML 预处理，已在 v1 引入）
- Pydantic v2（schema 校验，项目已有）

---

## 附录 A：v1 vs v2 对比

| 维度 | v1（已实现） | v2（本 spec） |
|------|-------------|--------------|
| 数据源 | SAIL /faculty/（单页） | 3 个实验室站点 People 页 |
| 解析层 | 代码 CSS 选择器 | LLM 驱动 |
| 子类 | 每站一个 collector 子类 + 钩子 | 零子类（config 驱动） |
| source_type | `lab_web` | `lab_web_site` |
| 角色 | 全 UNKNOWN（无头衔） | 四档映射（来自站点分区） |
| 覆盖 | 63 教授 | 教授 + 博士学生 + 博后 |
| 缓存 | 无 | HTML-hash 缓存复用 |
| 质量保障 | 选择器确定性 | schema 校验 + needs_review |
