# 行业人才库 — 架构设计方案

> 版本: v1.0 | 日期: 2026-08-01
> 状态: 设计已确认

---

## 1. 背景与目标

行业人才库是 AI4TALENT 的第四个人才域（`domains/industry/`），数据来源是
`smart-talent-sourcing` skill 产出的脉脉/LinkedIn 候选人 JSONL。

**核心原则："按岗招聘"**——以岗位为一等实体，寻源产出的人才通过关联表挂在岗位下，
同一个人才全局唯一，可出现在多个岗位中，每个岗位有独立的匹配分。

---

## 2. 关键决策

| 维度 | 决策 | 依据 |
|------|------|------|
| 岗位建模 | 一等实体（`industry_position` 表） | 按岗招聘是核心原则 |
| 人才唯一性 | 全局唯一（dedup_hash = sha256(name + current_org)） | 同一人才可出现在多个岗位 |
| 打分归属 | 关联表（同人对不同岗位匹配分不同） | 打分是岗位相关的 |
| 岗位管理 | 系统配置页面（管理员） | 岗位生命周期管理 |
| 用户前端 | 以岗位为入口展示候选人 | 招聘场景以岗位为中心 |
| 技术方向 | 关联 `core_tech_direction`（多选） | 技术领域太粗，方向才是岗位精度 |
| 导入策略 | 增量 upsert（保留用户编辑状态） | 保留 touched/status/notes |
| 架构 | 新建 `domains/industry/`，跨域隔离，独立表 | 跨域隔离铁律 |

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

### 3.2 `industry_talent`（人才，全局唯一）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `talent_id` | Integer | PK, autoincrement | |
| `name` | String(255) | NOT NULL, indexed | 姓名 |
| `current_org` | String(255) | nullable, indexed | 现任职公司 |
| `current_title` | String(255) | nullable | 现任职头衔 |
| `degree` | String(50) | nullable | 学历 |
| `years_of_exp` | String(20) | nullable | 工作年限 |
| `experiences` | JSON | default `[]` | 履历数组 `[{range/year, org, title}]` |
| `expect` | String(500) | nullable | 求职意向 |
| `location` | String(255) | nullable | 所在地 |
| `profile_url` | String(1000) | nullable | LinkedIn /in/ 或脉脉主页 |
| `photo_url` | String(1000) | nullable | 头像 |
| `source` | String(50) | nullable | 数据来源（maimai / linkedin） |
| `dedup_hash` | String(64) | NOT NULL, unique, indexed | sha256(name + current_org) |
| `unified_person_id` | String(100) | nullable, indexed | 预留跨库同一性 |
| `is_visible` | Boolean | NOT NULL, default True | |
| `created_at` / `updated_at` | DateTime | TimestampMixin | |

### 3.3 `industry_position_talent`（岗位-人才关联 + 打分）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | |
| `position_id` | Integer | FK→industry_position, NOT NULL, indexed | 岗位 |
| `talent_id` | Integer | FK→industry_talent, NOT NULL, indexed | 人才 |
| `match_score` | Float | nullable | 匹配分 0-100 |
| `match_tags` | JSON | default `[]` | 命中标签 |
| `match_reason` | Text | nullable | 推荐理由 |
| `touched` | Boolean | default False | 已触达 |
| `status` | String(20) | default 'new', indexed | new/contacted/interviewed/rejected/hired |
| `notes` | Text | nullable | 招聘备注 |
| `batch` | String(50) | nullable | 导入批次 |
| `source_platform` | String(50) | nullable | maimai / linkedin |
| `created_at` / `updated_at` | DateTime | TimestampMixin | |
| **Unique** | `(position_id, talent_id)` | | |

### 3.4 迁移

文件：`migrations/versions/056_add_industry_tables.py`

### 3.5 前置依赖

`core_tech_direction` 表当前为空，需填充种子数据（技术方向明细）。

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

### 增量 upsert

```
导入 JSONL（带 position_id）
  → 逐行解析
  → talent: 按 dedup_hash upsert（更新基本信息，不影响关联表状态）
  → position_talent: 按 (position_id, talent_id) upsert
    → 更新 match_score/tags/reason/batch
    → 保留 touched/status/notes（仅新关联记录才用默认值）
```

### JSONL 字段映射

| JSONL 字段 | → 目标 |
|------------|--------|
| name + current_org | talent.dedup_hash |
| name/current/current_org | talent 基本信息字段 |
| degree/years/experiences | talent 学历/年限/履历 |
| expect/location/profile_url | talent 意向/位置/链接 |
| match_score/match_tags/match_reason | position_talent 打分字段 |
| batch/source platform | position_talent 批次/来源 |

### 导入入口

| 入口 | 鉴权 |
|------|------|
| POST /api/v1/industry/import | 静态 API Key（skill 推送） |
| POST /api/v1/industry/import/upload | super_admin（管理员上传） |

---

## 6. API 设计

### 岗位管理

```
POST   /api/v1/industry/positions
GET    /api/v1/industry/positions
GET    /api/v1/industry/positions/{id}
PUT    /api/v1/industry/positions/{id}
DELETE /api/v1/industry/positions/{id}
```

### 人才列表（全局）

```
GET    /api/v1/industry/talents
  Query: page, page_size, keyword, position_id, min_score, status,
         source_platform, tech_direction, sort_by
  Response: PaginatedResponse<IndustryTalentSummary>
    # Summary = 基本信息 + 最高匹配分 + 命中的岗位列表 + 招聘状态
```

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

行业人才库与其他域（学术/开源/AI Native）保持一致的人才发现体验，而非招聘工具式的管理界面。

**展现维度：以人才为主，岗位为筛选**

- 用户进入行业人才库看到的是**人才列表**（全局人才池），和学术库/AI Native 库的浏览模式一致
- 岗位在这个体系里的角色是**筛选维度**和**匹配标记**，不是组织主线：
  - 筛选栏支持按"在招岗位"筛选（"哪些人命中了大模型推理工程师岗位"）
  - 人才卡片上标注该人命中的岗位 + 最高匹配分
  - 人才详情页展示多岗位匹配分对比

**视觉原则：与全库一致**

- 卡片网格布局（不是表格/列表），和学术库/AI Native 库同样的浏览体验
- 匹配分作为卡片上的视觉锚点（彩色分数 + 命中标签），但不改变整体布局节奏
- 紫色域主题（`#6B46C1`）用于导航/选中态，数据展示区用中性色

**交互原则：筛选 + 状态流转**

- 筛选栏置顶 sticky，支持多维度即时筛选（关键词/岗位/匹配分/状态/来源/技术方向）
- 招聘状态（new/contacted/interviewed/rejected/hired）通过标签颜色区分
- 状态变更是常见操作，支持列表页快捷修改（不强制进详情页）

### 7.2 页面结构

| 页面 | 路由 | 功能 |
|------|------|------|
| **人才列表** | `/industry` | 全局人才池卡片网格；筛选栏（关键词/岗位/匹配分/状态/来源/技术方向）；匹配分排序 |
| **人才详情** | `/industry/talents/{id}` | 基本信息 + 履历时间线 + 三维打分（院校/企业/方向）+ 多岗位匹配分对比 + 招聘状态管理 |

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
| **岗位匹配** | 该人才在各岗位下的匹配分对比（横向条形图或卡片列表：岗位名 + 匹配分 + 三维分数 + 状态） |

### 7.5 管理员（系统配置）

| 位置 | 功能 |
|------|------|
| "行业人才岗位" tab | 岗位 CRUD（含部门/技术方向/职级范围） |
| "行业人才导入" tab | 选岗位 + 上传 JSONL |

### 7.6 导航

主导航新增"行业人才"入口，与学术/开源/AI Native 并列，紫色域主题。

---

## 8. 不做的事（YAGNI）

- ❌ 跨库同一性识别
- ❌ 采集任务管理
- ❌ 后端重打分
- ❌ JD LLM 解析
- ❌ 向量嵌入/语义搜索

---

## 9. 实施顺序

1. 种子：core_tech_direction 填充
2. 数据层：三表模型 + 迁移
3. 导入服务：JSONL 解析 + 增量 upsert
4. API：人才列表 + 人才详情 + 岗位 CRUD + 状态管理
5. 系统配置：岗位管理 + 导入 tab
6. 前端：人才列表页 + 人才详情页 + 导航
