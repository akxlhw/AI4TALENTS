# AI 实验室人才库 — 架构设计方案

> 版本: v1.0 | 日期: 2026-07-02
> 状态: 已实现（v3.0.0，2026-07-14 发布）

---

## 1. 背景与目标

智能人才库（AI4TALENT）当前已建成学术人才库（OpenAlex）与开源人才库（GitHub）。本方案新增
**AI 实验室人才库**（以下简称 lab 库），覆盖 OpenAI / DeepMind / Stanford AI Lab 等顶尖 AI 实验室
的研究人员（教授、研究员、博后、博士生）。

数据来源方式与现有库不同：**不直接采集**，而是通过独立的 hermes agent 调用
`ai-lab-talent-crawler` skill 抓取实验室官网人员页面，产出标准 JSONL，再由 AI4Talent 的导入服务消费。

### 设计目标

1. 提供 lab 人才的浏览、搜索、详情能力（独立第四库产品形态）
2. 支持 hermes 自动推送 + 管理员手动上传两种导入入口
3. 严格遵守项目跨域隔离铁律（`AGENTS.md` 架构约束）

---

## 2. 关键决策（brainstorming 阶段确认）

| 维度 | 决策 | 依据 |
|------|------|------|
| 产品定位 | 独立第四库（独立入口 + 独立页面） | 用户选择 |
| 架构方向 | 新建 `domains/lab/` 独立域 + 独立 `lab_talent` 表 | **跨域隔离铁律**：新域不得 import `domains.academic`，故无法复用 `core_talent` |
| crawler 契约 | 同步修订 | importer-contract.md 原假设写 `core_talent`，需改为 `lab_talent` |
| 导入链路 | hermes 推送 API + 管理员手动上传，两者都支持 | 用户选择 |
| 导入策略 | 按实验室全量替换（先 DELETE 再 INSERT，单事务原子性） | 用户选择 |
| 跨库同人 | 现阶段不识别，预留 `unified_person_id` 字段 | 用户选择（MVP） |
| 前端范围 | 完整页面（概览 + 搜索 + 详情），首版不做收藏/人才池 | 用户选择 |
| hermes 鉴权 | 静态 API Key（存于 system_config） | 用户选择 |

### 为什么不复用 `core_talent` 表

`core_talent` 属于 `domains/academic/`。AGENTS.md 跨域隔离铁律规定域之间不得互相导入内部模块。
若新建 `domains/lab/`，则**绝不能 import `domains.academic.models.talent`**，复用 `core_talent` 即违规
（会被 `scripts/check_architecture.py` CI 拦截）。故必须新建独立表。

crawler 的 `importer-contract.md` 原本预设写 `core_talent`，是站在 crawler 视角写、未考虑 AI4Talent
架构约束的产物。本设计确定：**架构约束优先，契约服从架构**，同步修订 crawler。

---

## 3. 数据模型

### 3.1 核心表：`lab_talent`

文件位置：`backend/app/domains/lab/models/lab_talent.py`（新建）

| 字段 | 类型 | 约束 | 来源 JSONL 字段 | 说明 |
|------|------|------|----------------|------|
| `talent_id` | Integer | PK, autoincrement | — | 主键 |
| `name` | String(255) | NOT NULL, indexed | `name` | 姓名（标准化去多余空白）|
| `role_section` | String(100) | NOT NULL | `role_section` | 页面分区原始标签（Faculty/PhD Students/Postdocs/Staff/Alumni）|
| `role_type` | String(20) | NOT NULL, indexed, default `unknown` | （由 `role_section` 映射） | 标准化角色，复用 `domains/shared/models/enums.py` 的 `RoleType` 枚举值 |
| `academic_level` | String(20) | nullable, indexed | （由 `role_section` 映射，仅学生角色有值） | 学位层次：`phd` / `master` / `bachelor`；非学生角色为 NULL。见 §3.1 映射说明 |
| `current_title` | String(255) | nullable | `role_raw` | bio 详情页精确头衔原文 |
| `homepage` | String(500) | nullable | `homepage` | 个人主页 URL |
| `email` | String(255) | nullable | `email` | 邮箱 |
| `department` | String(255) | nullable | `department` | 院系/专业 |
| `research_areas` | JSON | nullable, default `[]` | `research_areas` | 研究方向数组 |
| `cohort_year` | Integer | nullable, indexed | `cohort_year` | PhD 入学/加入年份 |
| `cohort_source` | String(255) | nullable | `cohort_source` | 届别推断来源（`<来源类型>:<原文片段>`）|
| `lab_name` | String(255) | NOT NULL, indexed | `lab_name` | 子实验室/研究组（如 Stanford NLP Group）|
| `parent_lab` | String(255) | NOT NULL, indexed | `parent_lab` | 顶层实验室（对应 labs.yaml 的 name）|
| `source_url` | String(1000) | nullable | `source_url` | 采集该人员的列表页 URL |
| `source_detail_url` | String(1000) | nullable | `source_detail_url` | bio 详情页 URL |
| `collected_at` | DateTime | nullable | `collected_at` | ISO8601 采集时间戳 |
| `dedup_hash` | String(64) | NOT NULL, unique, indexed | （`sha256(name + lab_name + role_section)`） | 去重键（导入事务一致性保障）|
| `unified_person_id` | String(100) | nullable, indexed | — | 预留：未来跨库同一性识别 |
| `is_visible` | Boolean | NOT NULL, default True | — | 可见性控制（支持软隐藏）|
| `created_at` | DateTime | NOT NULL, server_default now() | — | TimestampMixin |
| `updated_at` | DateTime | NOT NULL, server_default now() | — | TimestampMixin |

#### `role_section` → `role_type` 映射

文件位置：`backend/app/domains/lab/constants/role_mapping.py`

| role_section（原始） | role_type | academic_level | 说明 |
|---------------------|-----------|----------------|------|
| Faculty / Professors / Principal Investigators | `professor` | NULL | 教授/PI |
| Postdocs / Postdoctoral | `graduate` | NULL | 博后 |
| Staff / Researchers / Research Scientists | `graduate` | NULL | 研究员归入 graduate（早期研究者语义）|
| PhD Students / Doctoral Students / PhD Candidates / 博士生 | `student` | `phd` | 博士生 |
| Master Students / Master's Students / Masters / 硕士生 | `student` | `master` | 硕士生 |
| Undergrads / Undergraduate Students / Bachelor / 本科生 | `student` | `bachelor` | 本科生 |
| Students（未细分的泛称）| `student` | NULL | 页面未区分学位层次时，level 留空 |
| Alumni / Former Members | `alumni` | NULL | 已毕业（独立 role_type，v3.0.0 变更）|
| 其他/Unknown | `unknown` | NULL | 兜底 |

#### 设计说明：role_type 与 academic_level 是正交两个维度

- `role_type`（复用 shared 域 `RoleType` 枚举）：粗粒度角色身份，与学术库保持一致语义
- `academic_level`（lab 库专属字段）：学位层次细分，**仅学生角色（role_type=student）有值**，其他角色为 NULL
- 不扩展 `RoleType` 枚举新增 phd/master 值 —— 避免污染 shared 域枚举（学术库的 student 是按论文数推断的，与 lab 的学位层次语义不同，混用会乱）
- `academic_level` 可索引，支持前端按"博士/硕士/学士"独立筛选

#### 映射实现（`constants/role_mapping.py`）

映射函数同时输出 role_type 和 academic_level，基于 role_section 的关键词匹配：

```python
def map_role(role_section: str) -> tuple[str, str | None]:
    s = role_section.lower()
    # 学位层次优先判断（在 student 大类内细分）
    if any(k in s for k in ["phd", "doctoral", "博士"]):
        return ("student", "phd")
    if any(k in s for k in ["master", "硕士"]):
        return ("student", "master")
    if any(k in s for k in ["undergrad", "bachelor", "本科"]):
        return ("student", "bachelor")
    if any(k in s for k in ["student", "学生"]):
        return ("student", None)  # 泛称学生，未细分
    if any(k in s for k in ["faculty", "professor", "pi", "教授"]):
        return ("professor", None)
    if any(k in s for k in ["postdoc", "博后"]):
        return ("graduate", None)
    if any(k in s for k in ["staff", "researcher", "研究员"]):
        return ("graduate", None)
    return ("unknown", None)
```

### 3.2 不做的关联表（首版）

| 候选表 | 决策 | 理由 |
|--------|------|------|
| 技术标签表 | 不做 | lab 人才无 OpenAlex 概念体系，`research_areas` 字段已足够 |
| 代表作表 | 不做 | crawler 不抓论文，首版无数据来源 |
| 收藏/人才池表 | 不做 | 用户决策：首版不做收藏；现有 `iam_favorite_talent` FK 指向 `core_talent`，跨表复用需改造，留待后续 |

### 3.3 Alembic 迁移

文件：`backend/migrations/versions/050_add_lab_talent_table.py`（新建）

- `down_revision` 指向当前 head（`049_add_genealogy_tables` 之后）
- `op.create_table('lab_talent', ...)` 按上表字段
- 索引：`ix_lab_talent_name`、`ix_lab_talent_parent_lab`、`ix_lab_talent_lab_name`、
  `ix_lab_talent_role_type`、`ix_lab_talent_academic_level`、`ix_lab_talent_cohort_year`、
  `ix_lab_talent_dedup_hash`(unique)、`ix_lab_talent_unified_person_id`
- 注册到 `backend/app/model_registry.py`：`from app.domains.lab.models.lab_talent import CoreLabTalent`

---

## 4. 后端架构（`domains/lab/`）

### 4.1 目录结构

```
backend/app/domains/lab/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── import_endpoint.py     # hermes 推送 + 管理员上传入口
│   ├── talents.py             # 列表/搜索/详情 API
│   └── stats.py               # 概览统计 API
├── models/
│   ├── __init__.py
│   └── lab_talent.py          # lab_talent ORM
├── schemas/
│   ├── __init__.py
│   └── lab_talent.py          # Pydantic DTO
├── repositories/
│   ├── __init__.py
│   └── lab_talent_repository.py
├── services/
│   ├── __init__.py
│   ├── lab_import_service.py  # JSONL 解析 + 全量替换核心
│   ├── lab_talent_service.py  # 列表/搜索/详情业务
│   └── lab_stats_service.py   # 概览统计
└── constants/
    ├── __init__.py
    └── role_mapping.py        # role_section → role_type
```

### 4.2 架构合规性自检

- ✅ 不 import `domains.academic.*` 或 `domains.open_source.*`（跨域铁律）
- ✅ 复用 `domains.shared.models.enums.RoleType`（枚举共享是允许的例外，AGENTS.md 明确）
- ✅ 复用 `app.core.*`（database / auth / config / exceptions）
- ✅ 路由注册到 `app/api_router.py`，模型注册到 `app/model_registry.py`
- ✅ Endpoint → Service → Repository 严格分层（AGENTS.md P0-5）
- ✅ HTTP 出站请求（如有）通过 `HttpClientFactory`（lab 库首版无主动出站，仅接收导入）

### 4.3 分层职责

| 层 | 职责 | 关键类 |
|----|------|--------|
| API（`api/`） | HTTP 处理 + Pydantic 校验，不直接碰 Repository | `import_endpoint` / `talents` / `stats` |
| Service（`services/`） | 业务编排（JSONL 解析、全量替换事务、搜索筛选）| `LabImportService` / `LabTalentService` / `LabStatsService` |
| Repository（`repositories/`） | 数据库 CRUD | `LabTalentRepository` |

---

## 5. 导入流程

### 5.1 两个入口共享一个核心 Service

```
hermes agent ──────► POST /api/v1/lab/import        (静态 API Key 鉴权)
管理员后台 ────────► POST /api/v1/lab/import/upload (require_super_admin)
                                  │
                                  ▼
                  LabImportService.import_jsonl(jsonl_bytes, parent_lab)
```

两个 HTTP 入口仅鉴权方式不同，核心导入逻辑只写一份。

### 5.2 `LabImportService.import_jsonl` 流程（按实验室全量替换）

1. **JSONL 校验**（对应 crawler 契约校验规则）：
   - 逐行解析 JSON；非法行跳过 + 记日志（不中断整体导入）
   - 每行必须有非空 `name`；否则丢弃
   - 每行必须有 `parent_lab` / `source_url` / `collected_at`；缺失则跳过 + 记日志
2. **字段映射**：按 §3.1 字段表映射 JSONL → `CoreLabTalent`
3. **`role_section` → `role_type`**：经 `constants/role_mapping.py` 映射
4. **计算 `dedup_hash`**：`sha256(f"{name}|{lab_name}|{role_section}")`
5. **按 `parent_lab` 全量替换**（单事务原子性）：
   ```python
   async with session.begin():
       await repo.delete_by_parent_lab(parent_lab)
       await repo.bulk_insert(parsed_talents, batch_size=500)
   ```
   - DELETE 与 INSERT 在同一事务，失败一起回滚，绝不丢数据
   - INSERT 分批（每批 500 行），避免 asyncpg 参数上限
6. **返回导入报告**：
   ```json
   {
     "parent_lab": "Stanford AI Lab",
     "total_lines": 187,
     "total_parsed": 182,
     "inserted": 182,
     "skipped": 5,
     "skip_reasons": [{"line": 23, "reason": "missing name"}, ...]
   }
   ```

### 5.3 hermes 鉴权（静态 API Key）

- API Key 存于 `sys_config` 表（复用 `ConfigService`），key 名：`lab_import_api_key`
- import API 校验 `Authorization: Bearer <key>` 与配置值匹配
- 不走 JWT 体系（机器对机器，无过期问题）
- 管理员可在系统配置页生成/轮换 key

---

## 6. API 设计

### 6.1 导入 API

```
POST /api/v1/lab/import                      # hermes 推送（API Key 鉴权）
POST /api/v1/lab/import/upload               # 管理员手动上传（require_super_admin）
```

请求（两个端点一致）：
```
Content-Type: multipart/form-data
  file:        <jsonl 文件>
  parent_lab:  "Stanford AI Lab"             # 必填，标识本次导入的顶层实验室
```

响应：
```json
{
  "parent_lab": "Stanford AI Lab",
  "total_lines": 187,
  "total_parsed": 182,
  "inserted": 182,
  "skipped": 5,
  "skip_reasons": [...]
}
```

### 6.2 浏览/搜索 API

```
GET /api/v1/lab/talents                      # 列表搜索
  Query:
    page=1, page_size=20
    keyword                                  # 姓名模糊搜索
    parent_lab                               # 顶层实验室筛选
    lab_name                                 # 子实验室筛选
    role_type                                # 角色筛选（professor/student/...）
    academic_level                           # 学位层次筛选（phd/master/bachelor，仅学生有效）
    research_area                            # 研究方向筛选（JSON 数组包含）
    cohort_year_gte                          # 入学年份下限
    sort_by                                  # name_asc / cohort_desc / created_desc
  Response: PaginatedResponse<LabTalentItem>

GET /api/v1/lab/talents/{talent_id}          # 详情
  Response: LabTalentDetail

GET /api/v1/lab/stats                        # 概览统计
  Response: {
    total_talents, total_parent_labs, total_sub_labs,
    parent_lab_distribution: [{parent_lab, count}],
    role_distribution: [{role_type, count}],
    top_labs: [{lab_name, count}]
  }
```

### 6.3 路由注册

`app/api_router.py` 新增：
```python
from app.domains.lab.api import import_endpoint, talents, stats
api_router.include_router(import_endpoint.router)
api_router.include_router(talents.router)
api_router.include_router(stats.router)
```

---

## 7. 前端

### 7.1 页面结构

| 页面 | 路由 | 组件 | 功能 |
|------|------|------|------|
| 概览 | `/lab` | `LabOverviewPage` | 总人数/实验室数/角色分布统计 + 热门实验室卡片 + Top 人才 |
| 搜索 | `/lab/search` | `LabSearchPage` | 筛选栏（parent_lab/lab_name/role_type/academic_level[博/硕/学]/research_area/cohort_year）+ 结果列表 + 分页排序 |
| 详情 | `/lab/talents/:id` | `LabTalentDetailPage` | 基本信息 + 研究方向 + 实验室归属 + 采集来源（无收藏按钮，首版不做）|

### 7.2 导航入口

主导航（`MainLayout.tsx`）新增"AI 实验室人才"菜单项，与"学术人才""开源人才"并列。

### 7.3 技术栈与 API 客户端

- 复用项目栈：React 18 + TS + AntD v5 + React Query + Zustand
- 新增 API 客户端：`frontend/src/services/api/lab.ts`
- 聚合入口 `frontend/src/services/api.ts` 按需导出

---

## 8. crawler 契约同步修订

`ai-lab-talent-crawler` skill 的两份参考文件需修订（与本设计对齐）：

### 8.1 `references/output-schema.md`

字段定义**不变**（JSONL schema 本身没问题，是 importer 端的映射目标变了）。

### 8.2 `references/importer-contract.md`（主要修订点）

| 原内容 | 修订为 |
|--------|--------|
| 字段映射目标 `core_talent` | 改为 `lab_talent` |
| `source_type = 'lab_web_site'` 隔离机制 | 删除（lab 库是独立表，不再用 source_type 隔离）|
| upsert 查询 `WHERE source_type='lab_web_site'` | 改为按 `parent_lab` 全量替换（DELETE + INSERT）|
| `(name+lab_name+role_section 的 sha256) → source_record_id` | 改为 `→ dedup_hash` |
| 触发命令 `import-lab-talent --file` | 改为 `POST /api/v1/lab/import`（API 形态）|
| 新增：hermes 鉴权方式 | 静态 API Key（`Authorization: Bearer <lab_import_api_key>`）|

---

## 9. 不做的事（YAGNI）

- ❌ 不做跨库同一性识别（仅预留 `unified_person_id` 字段）
- ❌ 不做收藏/人才池（首版）
- ❌ 不做技术标签/代表作关联表
- ❌ 不做 lab 人才的语义搜索/JD 匹配/向量嵌入（无论文数据，首版无意义）
- ❌ 不做采集任务管理（数据由外部 hermes 产出，AI4Talent 只负责导入）

---

## 10. 实施顺序建议

1. **后端数据层**：模型 + 迁移 + 注册（`lab_talent` 表）
2. **导入服务**：`LabImportService` + 导入 API（hermes 推送 + 管理员上传）+ API Key 鉴权
3. **crawler 契约修订**：同步改 `importer-contract.md`
4. **端到端导入验证**：用 crawler 产出的真实 JSONL 跑通一次导入
5. **浏览/搜索服务 + API**：列表/详情/统计
6. **前端三页面**：概览 + 搜索 + 详情
7. **导航与集成**：MainLayout 菜单 + 路由

---

## 11. 风险与待确认

| 风险/待确认项 | 说明 | 处置 |
|--------------|------|------|
| 学生角色细分（博/硕/学士）| 已用独立 `academic_level` 字段解决（见 §3.1），不扩展 shared 域 RoleType 枚举 | 设计已处置；学位层次与角色身份正交，语义清晰 |
| 全量替换事务时长 | 单实验室 >2000 人时 DELETE+INSERT 事务较长 | lab 单实验室规模通常 <2000，可接受；若超限后续改分批提交 |
| hermes 与 AI4Talent 的网络可达性 | 企业内网部署，hermes 需能访问 AI4Talent 的 import API | 部署时确认网络策略 |
| JSONL 大文件上传 | multipart 上传超大文件可能超时 | 首版按现有 upload 机制；超限场景后续改流式/分片 |
