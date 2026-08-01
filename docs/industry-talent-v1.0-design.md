# 行业人才库 — 架构设计方案

> 版本: v1.1 | 日期: 2026-08-01
> 状态: 设计评审修订版（v1.0 评审意见已全部吸收）
> 目标版本: V5.0.0

---

## 1. 背景与目标

行业人才库是 AI4TALENT 的第四个人才域（`domains/industry/`），数据来源是
`smart-talent-sourcing` skill 产出的脉脉/LinkedIn 候选人 JSONL。

**两条总体原则（用户确认）：**

1. **呈现一致性是基本原则**：人才库的呈现（视觉、交互）与整体人才库保持一致——
   以人才为主线的发现体验，与学术/开源/AI Native 库对齐。
2. **按岗招聘是辅助支撑**：以岗位维度给候选人打标签、按岗位维度筛选，
   岗位不作为导航主线。

**数据来源原则**：行业人才库不直接实现数据采集。采集由独立的 skill
（脉脉/LinkedIn 招聘平台）完成，本域的核心是数据结构与架构设计
（前端、后端、管理后台），通过 JSONL 导入契约与 skill 解耦。

---

## 2. 关键决策

| 维度 | 决策 | 依据 |
|------|------|------|
| 岗位建模 | 一等实体（`industry_position` 表） | 按岗招聘是核心定位 |
| 人才唯一性 | 全局唯一（dedup_hash，见 3.2 规则） | 同一人才可出现在多个岗位 |
| 打分归属 | 关联表（同人对不同岗位匹配分不同） | 打分是岗位相关的 |
| 岗位管理 | 系统配置页面（管理员） | 岗位生命周期管理 |
| 用户前端 | 以人才为主线呈现，岗位作为标签与筛选维度 | 呈现一致性是基本原则；按岗招聘是辅助支撑 |
| 技术方向 | 关联 `core_tech_direction`（多选） | 技术领域太粗，方向才是岗位精度 |
| 导入策略 | 增量 upsert（保留用户编辑状态） | 保留 touched/status/notes；空字段不覆盖；缺席不删除 |
| 架构 | 新建 `domains/industry/`，跨域隔离，独立表 | 跨域隔离铁律 |
| 数据采集 | 不在域内实现，由 skill 产出 JSONL 导入 | 采集与平台解耦 |

### 为什么不复用 `core_talent`

同 lab/competition 域：跨域隔离铁律禁止新域 import academic 的模型。
必须独立表。

---

## 3. 数据模型（三张表）

### 3.1 `industry_position`（岗位）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `position_id` | Integer | PK, autoincrement | |
| `title` | String(255) | NOT NULL, indexed | 岗位名称 |
| `department` | String(255) | nullable | 所属部门 |
| `tech_direction_codes` | JSON | default `[]` | 技术方向编码数组（关联 core_tech_direction） |
| `level_min` | Integer | nullable | 职级下限（如 19） |
| `level_max` | Integer | nullable | 职级上限（如 20） |
| `jd_text` | Text | nullable | JD 原文 |
| `jd_features` | JSON | nullable | JD 特征（技能/经验/目标公司） |
| `status` | String(20) | NOT NULL, default 'open', indexed | open / closed / archived |
| `created_by` | Integer | FK→iam_user_account | 创建者 |
| `created_at` / `updated_at` | DateTime | TimestampMixin | |

**删除策略**：岗位不提供物理删除。生命周期通过 `status` 流转
（open → closed → archived），归档岗位的关联数据完整保留，
前端默认不展示 archived 岗位。

### 3.2 `industry_talent`（人才，全局唯一）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `talent_id` | Integer | PK, autoincrement | |
| `name` | String(255) | NOT NULL, indexed | 姓名 |
| `current_org` | String(255) | nullable, indexed | 现任职公司 |
| `current_title` | String(255) | nullable | 现任职头衔 |
| `degree` | String(50) | nullable | 学历 |
| `years_of_exp` | String(20) | nullable | 工作年限（原始文本，展示用） |
| `years_of_exp_num` | Float | nullable | 工作年限（数值，筛选/排序用，导入时解析） |
| `experiences` | JSON | default `[]` | 履历数组 `[{range/year, org, title}]` |
| `expect` | String(500) | nullable | 求职意向 |
| `location` | String(255) | nullable | 所在地 |
| `profile_url` | String(1000) | nullable | LinkedIn /in/ 或脉脉主页 |
| `photo_url` | String(1000) | nullable | 头像 |
| `source` | String(50) | nullable | 数据来源（maimai / linkedin） |
| `dedup_hash` | String(64) | NOT NULL, unique, indexed | 见下方规则 |
| `unified_person_id` | String(100) | nullable, indexed | 预留跨库同一性 |
| `is_visible` | Boolean | NOT NULL, default True | |
| `created_at` / `updated_at` | DateTime | TimestampMixin | |

**dedup_hash 规则：**

```
dedup_hash = sha256(normalize(name) + "|" + normalize(current_org) + "|" + normalize(current_title))
normalize(s) = 去首尾空白、全角转半角、连续空白压一格；空值统一为 ""
```

- 三要素联合 hash，避免 `current_org` 缺失时退化成纯姓名 hash
  导致同名不同人被合并（"王伟"问题）
- `current_org` 为空的记录导入时打 warning 日志（hash 区分度弱，需人工关注）
- **跨平台去重不在 dedup_hash 覆盖范围内**：脉脉（中文名）与 LinkedIn（英文名）
  对同一人几乎必然产生不同 hash，会形成两条记录。跨平台同一性识别属于
  YAGNI 项（见第 8 节），后续由 `unified_person_id` 承接

### 3.3 `industry_position_talent`（岗位-人才关联 + 打分）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | |
| `position_id` | Integer | FK→industry_position, NOT NULL, indexed | 岗位 |
| `talent_id` | Integer | FK→industry_talent, NOT NULL, indexed | 人才 |
| `match_score` | Float | nullable | 匹配总分 0-100 |
| `score_school` | Float | nullable | 院校维度分 0-100 |
| `score_company` | Float | nullable | 企业维度分 0-100 |
| `score_direction` | Float | nullable | 方向维度分 0-100 |
| `match_tags` | JSON | default `[]` | 命中标签 |
| `match_reason` | Text | nullable | 推荐理由 |
| `touched` | Boolean | default False | 已触达 |
| `status` | String(20) | default 'new', indexed | new/contacted/interviewed/rejected/hired |
| `notes` | Text | nullable | 招聘备注 |
| `batch` | String(50) | nullable | 导入批次 |
| `source_platform` | String(50) | nullable | maimai / linkedin |
| `created_at` / `updated_at` | DateTime | TimestampMixin | |
| **Unique** | `(position_id, talent_id)` | | |

三维子分数（院校/企业/方向）为可空字段：skill 产出则展示，
未产出时前端降级为仅展示总分。

### 3.4 迁移

文件：`migrations/versions/058_add_industry_tables.py`（`down_revision = '057'`）

> 编号说明：056/057 已被开源域占用（搜索索引、is_student 字段）。

### 3.5 前置依赖

`core_tech_direction` 表当前为空，需填充种子数据（技术方向明细）。
开源域 `os_repo_config.tech_direction_id` 已引用该表，种子脚本需与
开源域既有引用兼容；种子内容为手工定义的技术方向清单（实施步骤 1 交付）。

---

## 4. 后端架构（`domains/industry/`）

```
backend/app/domains/industry/
├── api/
│   ├── __init__.py
│   ├── positions.py         # 岗位 CRUD + 候选人列表
│   ├── talents.py           # 人才详情
│   └── import_endpoint.py   # JSONL 导入
├── models/
│   ├── __init__.py
│   └── industry.py          # 3 个模型
├── schemas/
│   ├── __init__.py
│   └── industry.py
├── repositories/
│   ├── __init__.py
│   └── industry_repository.py
├── services/
│   ├── __init__.py
│   ├── industry_import_service.py
│   ├── industry_position_service.py
│   └── industry_talent_service.py
└── constants/
    ├── __init__.py
    └── status_config.py     # 候选人状态映射
```

注册：`api_router.py` + `model_registry.py`。

---

## 5. 导入流程

### 增量 upsert（用户确认的三条边界规则）

```
导入 JSONL（带 position_id）
  → 逐行解析
  → talent: 按 dedup_hash upsert
    → 按非空字段更新基本信息（新版为空的字段保留库中旧值，不用空值覆盖）
  → position_talent: 按 (position_id, talent_id) upsert
    → 更新 match_score/三维子分数/tags/reason/batch
    → 保留 touched/status/notes（仅新关联记录才用默认值）
```

**边界规则（显式声明，防止实现走样）：**

1. **空字段不覆盖**：JSONL 中缺失/为空的字段不更新库中已有值
   （脉脉与 LinkedIn 数据丰满度不同，防止二次导入抹掉好数据）
2. **缺席不删除**：新批次中不存在的人才与关联不做任何处理
   ——本域不做竞赛域式的全量替换导入
3. **同一人进新岗位**：已有人才出现在新岗位的导入中，仅新增
   `(新岗位, 人才)` 关联记录，其在其他岗位下的打分与招聘状态不受影响

### JSONL 导入契约（schema v1.0）

每行一个候选人对象：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `position_id` | int | ✅ | 目标岗位（导入时由管理员/调用方指定，也可在行内覆盖） |
| `name` | string | ✅ | 姓名 |
| `current_org` | string | 建议 | 现任职公司（缺失时 dedup 区分度弱，打 warning） |
| `current_title` | string | 否 | 现任职头衔 |
| `degree` | string | 否 | 学历 |
| `years_of_exp` | string | 否 | 工作年限文本（如 "10年"），导入时解析出 `years_of_exp_num` |
| `experiences` | array | 否 | `[{range, org, title}]` |
| `expect` | string | 否 | 求职意向 |
| `location` | string | 否 | 所在地 |
| `profile_url` | string | 否 | 脉脉/LinkedIn 主页 |
| `photo_url` | string | 否 | 头像 |
| `source` | string | 否 | maimai / linkedin |
| `match_score` | float | 否 | 匹配总分 0-100 |
| `score_school` / `score_company` / `score_direction` | float | 否 | 三维子分数 |
| `match_tags` | array | 否 | 命中标签 |
| `match_reason` | string | 否 | 推荐理由 |
| `batch` | string | 否 | 导入批次标识 |

示例：

```json
{"position_id": 3, "name": "张三", "current_org": "亚马逊云科技", "current_title": "应用科学家", "degree": "博士", "years_of_exp": "10年", "location": "北京", "source": "maimai", "match_score": 98, "score_school": 95, "score_company": 90, "score_direction": 99, "match_tags": ["顶级院校", "美企巨头", "LLM"], "match_reason": "CMU 博士，AWS 大模型推理团队 10 年", "batch": "2026-08-llm-inference"}
```

契约版本变更需向后兼容（只增字段不改语义），skill 与导入服务按此契约联调。

### 导入入口

| 入口 | 鉴权 | 说明 |
|------|------|------|
| POST /api/v1/industry/import/upload | super_admin | 管理员上传 JSONL（v1 主入口） |
| POST /api/v1/industry/import | 静态 API Key | skill 推送通道（v1 可暂缓，见下） |

**API Key 推送通道**：现有 lab/competition 域均为管理员上传，无机器推送先例。
若 v1 启用该通道，需补齐：API Key 配置项与校验依赖、权限边界（仅限导入）、
调用审计（来源/批次/行数入库）、失败告警。否则 v1 只保留管理员上传。

---

## 6. API 设计

### 岗位管理

```
POST   /api/v1/industry/positions
GET    /api/v1/industry/positions
GET    /api/v1/industry/positions/{id}
PUT    /api/v1/industry/positions/{id}     # 含 status 流转（open/closed/archived）
```

不提供 DELETE（见 3.1 删除策略）。

### 人才列表（全局）

```
GET    /api/v1/industry/talents
  Query: page, page_size, keyword, position_id, min_score, status,
         source_platform, tech_direction, sort_by
  sort_by: match_score_desc（默认）/ match_score_asc / created_desc
  Response: PaginatedResponse<IndustryTalentSummary>
    # Summary = 基本信息 + 最高匹配分 + 命中的岗位列表 + 招聘状态
```

> 实现注意：Summary 的「命中岗位列表 + 最高分」需 join 关联表聚合，
> 用一条 GROUP BY 子查询完成，禁止逐人才查询（N+1）。

### 人才详情

```
GET    /api/v1/industry/talents/{talent_id}
  # 含完整履历 + 该人才在各岗位下的匹配分对比

GET    /api/v1/industry/talents/{talent_id}/positions
  # 该人才在哪些岗位下出现过 + 各岗位匹配分
```

### 候选人状态管理

```
PATCH  /api/v1/industry/talents/{talent_id}/positions/{position_id}
  Body: { status?, touched?, notes? }
  # 更新人才在某岗位下的招聘状态
```

---

## 7. 前端

### 7.1 设计原则

行业人才库与其他域（学术/开源/AI Native）保持一致的人才发现体验，
而非招聘工具式的管理界面。**呈现一致性是最基本的原则。**

**展现维度：以人才为主，岗位为标签与筛选**

- 用户进入行业人才库看到的是**人才列表**（全局人才池），和学术库/AI Native 库的浏览模式一致
- 岗位在这个体系里的角色是**标签维度**和**筛选维度**（按岗招聘的辅助支撑）：
  - 筛选栏支持按"在招岗位"筛选（"哪些人命中了大模型推理工程师岗位"）
  - 人才卡片上标注该人命中的岗位 + 最高匹配分
  - 人才详情页展示多岗位匹配分对比

**视觉原则：与全库一致**

- 卡片网格布局（不是表格/列表），和学术库/AI Native 库同样的浏览体验
- 匹配分作为卡片上的视觉锚点（彩色分数 + 命中标签），但不改变整体布局节奏
- 紫色域主题（`#6B46C1`）用于导航/选中态，数据展示区用中性色；
  需接入 `applyDomainCssVars` 域注册机制（`'industry'`）

**交互原则：筛选 + 状态流转**

- 筛选栏置顶 sticky，支持多维度即时筛选（关键词/岗位/匹配分/状态/来源/技术方向）
- 招聘状态（new/contacted/interviewed/rejected/hired）通过标签颜色区分
- 状态变更是常见操作，支持列表页快捷修改（不强制进详情页）

### 7.2 页面结构

| 页面 | 路由 | 功能 |
|------|------|------|
| **人才列表** | `/industry` | 全局人才池卡片网格；筛选栏（关键词/岗位/匹配分/状态/来源/技术方向）；默认匹配分排序 |
| **人才详情** | `/industry/talents/{id}` | 基本信息 + 履历时间线 + 三维打分（院校/企业/方向，缺子分数时仅总分）+ 多岗位匹配分对比 + 招聘状态管理 |

### 7.3 人才卡片设计

卡片展示（与 AI Native 库的 LabTalentCard 同级精度）：

```
┌─────────────────────────────────────┐
│ [头像] 张三                    98 分 │ ← 匹配分（彩色：80+绿/65-79黄）
│        应用科学家 · 亚马逊云科技      │ ← current_title · current_org
│        博士 · 10年 · 北京             │ ← degree · years · location
│        [顶级院校] [美企巨头] [LLM]   │ ← match_tags（命中标签）
│        📋 大模型推理工程师            │ ← 命中的岗位（可多选标签）
│        ○ new（状态标签）              │ ← 招聘状态
└─────────────────────────────────────┘
```

### 7.4 人才详情页

Tabs 分区（参照 AI Native 库的详情页模式）：

| Tab | 内容 |
|-----|------|
| **基本信息** | 姓名/公司/职位/学历/年限/位置/求职意向/来源链接 |
| **履历时间线** | experiences[] 的可视化时间线：每段 = 公司 + 职位 + 时间范围；命中标签（顶级院校/美企）贴在对应履历段上 |
| **岗位匹配** | 该人才在各岗位下的匹配分对比（横向条形图或卡片列表：岗位名 + 总分 + 三维子分数 + 状态） |

### 7.5 管理员（系统配置）

| 位置 | 功能 |
|------|------|
| "行业人才岗位" tab | 岗位 CRUD（含部门/技术方向/职级范围；不提供物理删除，仅归档） |
| "行业人才导入" tab | 选岗位 + 上传 JSONL + 导入报告（新增/更新/跳过计数） |

### 7.6 导航

主导航"行业"入口解锁（当前为带锁的 demo 页 `demo-industry`），
正式页面上线后 demo 页退役，紫色域主题。

---

## 8. 不做的事（YAGNI）

- ❌ 跨库/跨平台同一性识别（dedup_hash 不覆盖，预留 unified_person_id）
- ❌ 采集任务管理（采集由 skill 完成，本域只有导入）
- ❌ 后端重打分
- ❌ JD LLM 解析
- ❌ 向量嵌入/语义搜索

---

## 9. 实施顺序

1. 种子：core_tech_direction 填充（与开源域既有引用兼容）
2. 数据层：三表模型 + 迁移 058
3. 导入服务：JSONL 解析 + 增量 upsert（空字段不覆盖/缺席不删除）
4. API：人才列表 + 人才详情 + 岗位 CRUD + 状态管理
5. 系统配置：岗位管理 + 导入 tab
6. 前端：人才列表页 + 人才详情页 + 导航（demo-industry 退役）

---

## 附：v1.1 修订记录（2026-08-01）

- 第 2 节：「用户前端」决策修正为「以人才为主线，岗位为标签与筛选维度」（呈现一致性原则）
- 3.1：明确岗位不提供物理删除，仅归档
- 3.2：dedup_hash 升级为三要素（name+org+title），空值归一规则，跨平台去重范围声明；新增 `years_of_exp_num`
- 3.3：关联表新增三维子分数字段（score_school/company/direction）
- 3.4：迁移编号修正为 058（056/057 已被开源域占用）
- 3.5：tech_direction 种子需与开源域既有引用兼容
- 第 5 节：增量导入三条边界规则显式化；新增 JSONL 导入契约 schema v1.0；API Key 通道启用条件
- 第 6 节：默认排序 match_score_desc；删除 DELETE 端点；列表聚合查询 N+1 警示
- 第 7 节：导航解锁与 demo 页退役；`applyDomainCssVars` 域注册
