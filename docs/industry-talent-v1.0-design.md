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

### 候选人列表

```
GET    /api/v1/industry/positions/{id}/candidates
  Query: page, page_size, keyword, min_score, status, source_platform, sort_by
```

### 人才详情

```
GET    /api/v1/industry/talents/{talent_id}
GET    /api/v1/industry/talents/{talent_id}/positions
```

### 候选人状态管理

```
PATCH  /api/v1/industry/positions/{id}/candidates/{talent_id}
  Body: { status?, touched?, notes? }
```

---

## 7. 前端

### 普通用户

| 页面 | 路由 | 功能 |
|------|------|------|
| 岗位列表 | `/industry` | open 岗位卡片列表 |
| 岗位候选人 | `/industry/positions/{id}` | 按 match_score 降序 + 筛选 |
| 人才详情 | `/industry/talents/{id}` | 基本信息 + 履历时间线 + 多岗位对比 |

### 管理员（系统配置）

| 位置 | 功能 |
|------|------|
| "行业人才岗位" tab | 岗位 CRUD |
| "行业人才导入" tab | 选岗位 + 上传 JSONL |

### 导航

主导航新增"行业人才"，紫色域主题（`#6B46C1`）。

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
4. API：岗位 CRUD + 候选人列表 + 人才详情 + 状态管理
5. 系统配置：岗位管理 + 导入 tab
6. 前端三页面 + 导航
