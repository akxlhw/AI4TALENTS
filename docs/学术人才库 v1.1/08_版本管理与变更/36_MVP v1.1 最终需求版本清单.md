# MVP v1.1 最终需求版本清单

**文档名称**：MVP v1.1 最终需求版本清单
**文档编号**：36
**版本**：V1.1
**状态**：最终版
**适用范围**：智能人才库—学术人才子系统 MVP v1.1
**编制日期**：2026-03-26
**更新日期**：2026-03-29

---

## 1. 版本概述

### 1.1 版本定义

**MVP v1.1 = 从"学校维度的学术人才浏览库"升级为"面向研发招聘的技术要素与国家院校双视角人才发现与轻量运营平台"**

### 1.2 版本价值

- 对业务部门：能直接从"技术要素"视角观察人才供给
- 对平台部门：能直接从"国家院校"视角观察人才覆盖
- 对管理侧：能以更低风险方式控制数据采集和发布
- 对招聘使用者：能在发现人才后继续完成轻量跟进

---

## 2. 变更需求清单（CR List）- 最终版

### 2.1 原始 CR 清单（已实现）

| 编号 | 变更项 | 优先级 | 状态 |
|------|--------|--------|------|
| CR-01 | 新增"技术要素"主视角 | P0 | ✅ 已完成 |
| CR-02 | 新增"国家院校"主视角 | P0 | ✅ 已完成 |
| CR-03 | 首页新增双主视角概要区 | P0 | ✅ 已完成 |
| CR-04 | 首页新增热点标签 | P0 | ✅ 已完成 |
| CR-05 | 搜索能力增强 | P0 | ✅ 已完成 |
| CR-06 | 人才详情招聘化增强 | P1 | ✅ 已完成 |
| CR-07 | 新增收藏/人才池/备注/跟进状态 | P0 | ✅ 已完成 |
| CR-08 | 建立技术要素与 OpenAlex 映射 | P0 | ✅ 已完成 |
| CR-09 | 新增采集范围配置 | P0 | ✅ 已完成 |
| CR-10 | 新增采集周期与执行参数配置 | P0 | ✅ 已完成 |
| CR-11 | 新增采集任务管理 | P0 | ✅ 已完成 |
| CR-12 | 新增数据版本与发布控制 | P0 | ✅ 已完成 |
| CR-13 | 新增数据质量摘要与轻量纠偏 | P1 | ✅ 已完成 |
| CR-14 | 权限模型扩展 | P0 | ✅ 已完成 |
| CR-15 | 导出能力增强 | P1 | ✅ 已完成 |

### 2.2 开发过程中优化新增的需求

| 编号 | 变更项 | 优先级 | 说明 |
|------|--------|--------|------|
| CR-16 | 采集配置简化设计 | P0 | 采用"技术要素→顶会顶刊→采集任务"简化流程，固定数据类型和时间范围 |
| CR-17 | Venue 配置层 | P0 | 新增顶会顶刊独立管理表（Venue），支持与技术要素的多对多绑定 |
| CR-18 | Raw 数据层 | P1 | 新增原始数据层模型（RawWork、RawAuthor、RawInstitution），支持数据回溯和审计 |
| CR-19 | 标准化数据层 | P1 | 新增标准化层模型（StdAuthor、StdSchool、SchoolNameAlias），支持学校归一 |
| CR-20 | 后台异步采集执行器 | P0 | 实现后台异步任务执行，支持任务进度实时更新 |
| CR-21 | 角色智能判断 | P0 | 实现基于论文数、引用数、h-index 的学者角色自动判断逻辑 |
| CR-22 | 人才技术归属追踪 | P1 | 新增 AuthorTechBelong 模型，追踪人才-技术要素-顶会顶刊的关系 |
| CR-23 | VenueSubTask 细粒度追踪 | P1 | 支持每个顶会顶刊的采集子任务追踪 |
| CR-24 | 院校机构文案统一与数据变更 | P0 | 统一"Top院校机构"为"院校机构"；首页热点数据改为API实时获取；区域新增"其他"分类 |

---

## 3. 功能需求详细说明

### 3.1 信息架构与导航（TP1）

**变更项**：CR-01, CR-02

#### 一级导航调整
| 序号 | 导航项 | 说明 |
|------|--------|------|
| 1 | 首页 | 统一入口，双主视角概要 |
| 2 | 技术要素 | 业务部门主视角 |
| 3 | 国家院校 | 平台部门主视角 |
| 4 | 人才搜索 | 跨视角统一检索 |
| 5 | 我的收藏 | 轻量运营收口 |
| 6 | 权限管理 | 用户与权限配置 |

#### 术语统一
- "技术类目" → "技术要素"
- 所有页面和字段统一使用新术语

---

### 3.2 首页增强（TP2）

**变更项**：CR-03, CR-04, CR-24

#### 基础统计区
| 指标 | 说明 |
|------|------|
| 已收录高校数 | 权限范围内的学校数量 |
| 教授类人才数 | 权限范围内的教授数量 |
| 学生类人才数 | 权限范围内的学生数量 |
| 总人才数 | 权限范围内的总人数 |
| 授权学校数 | 用户可见学校数 |
| 数据版本/更新时间 | 当前生效版本信息 |

#### 双主视角概要卡

**技术要素概要卡**：
- 技术要素数
- 技术方向数
- 人才总数
- 覆盖国家数
- 覆盖院校数
- 热门技术要素标签（按人才数Top6，点击跳转）

**国家院校概要卡**：
- 覆盖国家数
- 覆盖院校数
- 人才总数
- 覆盖技术要素数
- 主要国家标签（按人才数Top5，点击跳转）
- Top院校机构标签（按人才数Top5，点击跳转）

#### 首页热点数据API
- 端点：`GET /api/v1/homepage/highlights`
- 返回：热门技术要素、主要国家、Top院校机构（均按人才数排序）

---

### 3.3 技术要素页面（TP3）

**变更项**：CR-01

#### 筛选条件
| 字段 | 类型 | 说明 |
|------|------|------|
| 技术要素 | 下拉单选 | 一级分类 |
| 技术方向 | 下拉多选 | 二级细分 |
| 关键词 | 文本 | 姓名/研究方向 |
| 国家 | 下拉多选 | 所在国家 |
| 学校 | 下拉多选 | 所在学校 |
| 人才角色 | 下拉单选 | 教授/学生/已毕业 |
| 是否已毕业 | 下拉单选 | 可选 |
| 待确认状态 | 下拉单选 | 可选 |

#### Tab 页签
| Tab | 内容 |
|-----|------|
| 国家分布 | 按国家统计人才数量 |
| 院校分布 | 按学校统计人才数量 |
| 人才明细 | 人才列表，支持收藏/入池/详情 |

---

### 3.4 国家院校页面（TP4）

**变更项**：CR-02

#### 筛选条件
| 字段 | 类型 | 说明 |
|------|------|------|
| 区域 | 下拉单选 | 地理区域 |
| 国家 | 下拉多选 | 所属国家 |
| 学校 | 下拉多选 | 具体学校 |
| 技术要素 | 下拉单选 | 技术分类 |
| 技术方向 | 下拉多选 | 二级细分 |
| 关键词 | 文本 | 姓名/研究方向 |
| 人才角色 | 下拉单选 | 教授/学生/已毕业 |

#### Tab 页签
| Tab | 内容 |
|-----|------|
| 院校分布 | 按学校统计人才数量 |
| 技术要素分布 | 按技术要素统计人才数量 |
| 人才明细 | 人才列表，支持收藏/入池/详情 |

---

### 3.5 搜索增强（TP5）

**变更项**：CR-05

#### 新增筛选条件
| 字段 | 类型 | 说明 |
|------|------|------|
| 关键词 | 文本 | 姓名/研究方向/论文 |
| 技术要素 | 下拉单选 | 一级分类 |
| 技术方向 | 下拉多选 | 二级细分 |
| 区域 | 下拉单选 | 地理区域 |
| 国家 | 下拉多选 | 所属国家 |
| 学校 | 下拉多选 | 具体学校 |
| 人才角色 | 下拉单选 | 教授/学生/已毕业 |
| 是否已毕业 | 下拉单选 | 是/否 |
| 待确认状态 | 下拉单选 | 是/否 |

#### 搜索结果操作
- 排序（按引用数/h-index/论文数）
- 清空筛选
- 切换视图（卡片/表格）
- 收藏
- 加入人才池
- 查看详情

---

### 3.6 人才详情增强（TP5）

**变更项**：CR-06

#### 新增展示内容
| 字段 | 说明 |
|------|------|
| 技术标签 | 关联的技术要素和方向 |
| 招聘判断摘要 | 基于学术指标的招聘建议 |
| 代表成果摘要 | 近年高影响力论文 |
| 数据完整度 | 信息完整百分比 |
| 待确认项 | 需人工确认的信息 |

#### 运营动作
- 收藏/取消收藏
- 加入人才池
- 添加备注
- 设置跟进状态

---

### 3.7 收藏与人才池（TP6）

**变更项**：CR-07

#### 收藏功能
| 操作 | 说明 |
|------|------|
| 收藏人才 | 添加到个人收藏 |
| 取消收藏 | 从收藏列表移除 |
| 收藏列表 | 查看所有收藏人才 |
| 添加备注 | 为收藏人才添加备注 |
| 设置状态 | new_found/contacted/interviewed/rejected/hired |

#### 人才池功能
| 操作 | 说明 |
|------|------|
| 创建人才池 | 按专题创建人才池 |
| 加入人才池 | 将人才加入指定池 |
| 移出人才池 | 从池中移除人才 |
| 池列表管理 | 查看/归档/删除人才池 |

---

### 3.8 权限扩展（TP7）

**变更项**：CR-14

#### 三维权限模型
| 维度 | 说明 |
|------|------|
| 学校范围 | 可见的学校列表 |
| 国家范围 | 可见的国家列表 |
| 技术要素范围 | 可见的技术要素列表 |

#### 默认视角配置
- 用户可设置默认视角（技术要素/国家院校）
- 登录后自动跳转到默认视角页

#### 权限控制范围
- 首页统计和热点标签
- 技术要素页统计和列表
- 国家院校页统计和列表
- 搜索结果
- 人才详情
- 导出能力
- 后台配置操作

---

### 3.9 采集配置与任务管理（TP8）

**变更项**：CR-09, CR-10, CR-11, CR-16, CR-17, CR-20, CR-21

#### 简化设计理念
**技术要素 → 顶会顶刊 → 采集任务**

| 参数类型 | 参数 | 配置方式 |
|---------|------|---------|
| 固定参数 | 数据类型 | 学者、论文、机构（固定） |
| 固定参数 | 时间范围 | 2010.1.1 至今（固定） |
| 可配置参数 | 采集范围 | 技术要素关联的顶会顶刊 |
| 可配置参数 | 采集模式 | 全量/增量 |

#### 页面结构
| Tab | 内容 |
|-----|------|
| 技术要素配置 | 管理技术要素关联的顶会顶刊 |
| 采集任务 | 查看/管理采集任务 |

#### 技术要素配置
- 查看所有技术要素列表
- 配置关联的顶会顶刊（格式：`ID|名称|类型`）
- 启动采集任务（全量/增量）

#### 采集任务管理
| 字段 | 说明 |
|------|------|
| 任务编码 | 唯一标识 |
| 技术要素 | 关联的技术要素 |
| 采集模式 | 全量/增量 |
| 状态 | 待执行/执行中/已完成/失败/已取消 |
| 进度百分比 | 实时更新 |
| 当前步骤 | 正在采集的顶会顶刊名称 |
| 记录数统计 | 成功/失败/跳过 |
| 触发时间 | 任务启动时间 |

#### 后台异步执行器
- 用户请求 → 创建任务 → 启动后台任务
- 后台遍历顶会顶刊 → 调用 OpenAlex API
- 解析数据 → 入库 → 更新进度

#### 角色智能判断逻辑
| 条件 | 角色类型 | 置信度 |
|------|---------|--------|
| works_count >= 50 且 h_index >= 20 | 教授 | 95% |
| works_count >= 30 且 cited_by >= 1000 | 教授 | 90% |
| works_count >= 20 且 h_index >= 10 | 教授 | 85% |
| works_count <= 8 | 学生 | 80% |
| works_count <= 15 且 cited_by < 200 | 学生 | 75% |
| 8 < works_count < 20 | 已毕业 | 70% |
| 其他 | 教授 | 60% |

---

### 3.10 数据版本与发布（TP9）

**变更项**：CR-12

#### 版本管理
| 功能 | 说明 |
|------|------|
| 候选版本列表 | 采集完成后生成的版本 |
| 当前生效版本 | 标记为 active 的版本 |
| 版本统计 | 人才数/学校数/论文数 |
| 发布操作 | 手动发布候选版本 |
| 回滚操作 | 回滚到历史版本 |

#### 发布记录
- 记录每次发布/回滚操作
- 操作人、时间、备注

---

### 3.11 数据质量与纠偏（TP9）

**变更项**：CR-13

#### 质量摘要指标
| 类别 | 指标 |
|------|------|
| 人才质量 | 总数、有ORCID数、有机构数、有论文数、完整度均值 |
| 学校质量 | 总数、有ROR数、有国家数 |
| 论文质量 | 总数、有DOI数 |
| 技术标签 | 总数、已确认数、自动识别数、待确认数 |
| 问题统计 | 严重/警告/信息级别问题数 |

#### 纠偏操作
| 操作 | 说明 |
|------|------|
| 修正技术方向 | 手动修改人才的技术方向 |
| 修正角色 | 手动修改人才角色 |
| 标记待确认 | 标记为需人工确认 |
| 标记排除展示 | 从前台隐藏 |

---

### 3.12 导出增强（TP5）

**变更项**：CR-15

#### 导出范围
- 搜索结果导出
- 技术要素结果导出
- 国家院校结果导出
- 收藏/人才池结果导出

#### 导出约束
- 仅导出权限范围内数据
- 记录导出人、时间、条件

---

## 4. 数据模型清单

### 4.1 核心业务模型

| 模型 | 表名 | 说明 |
|------|------|------|
| TechElement | core_tech_element | 技术要素 |
| TechDirection | core_tech_direction | 技术方向 |
| TalentTechTag | core_talent_tech_tag | 人才技术标签 |

### 4.2 IAM 模型

| 模型 | 表名 | 说明 |
|------|------|------|
| UserAccount | iam_user_account | 用户账户（含 default_view） |
| UserSchoolScope | iam_user_school_scope | 三维权限范围 |
| FavoriteTalent | iam_favorite_talent | 收藏记录（含 followup_status） |
| TalentPool | iam_talent_pool | 人才池 |
| TalentPoolMember | iam_talent_pool_member | 人才池成员 |

### 4.3 同步与采集模型

| 模型 | 表名 | 说明 |
|------|------|------|
| CollectScope | sync_collect_scope | 采集范围配置 |
| CollectStrategy | sync_collect_strategy | 采集策略配置 |
| CollectTask | sync_collect_task | 采集任务 |
| VenueSubTask | sync_venue_sub_task | 顶会顶刊子任务 |

### 4.4 数据版本模型

| 模型 | 表名 | 说明 |
|------|------|------|
| DataVersion | data_version | 数据版本 |
| DataPublishRecord | data_publish_record | 发布记录 |
| DataCorrectionRecord | data_correction_record | 纠偏记录 |
| DataQualitySummary | data_quality_summary | 质量摘要 |

### 4.5 Venue 配置层（新增）

| 模型 | 表名 | 说明 |
|------|------|------|
| Venue | config_venue | 顶会顶刊配置 |
| VenueTechBinding | config_venue_tech_binding | Venue-技术要素绑定 |

### 4.6 Raw 数据层（新增）

| 模型 | 表名 | 说明 |
|------|------|------|
| RawWork | raw_work | 原始论文数据 |
| RawAuthor | raw_author | 原始作者数据 |
| RawInstitution | raw_institution | 原始机构数据 |
| AuthorTechBelong | rel_author_tech_belong | 作者-技术要素归属 |

### 4.7 标准化数据层（新增）

| 模型 | 表名 | 说明 |
|------|------|------|
| StdAuthor | std_author | 标准化作者 |
| StdSchool | std_school | 标准化学校 |
| SchoolNameAlias | std_school_alias | 学校名称别名 |

---

## 5. API 接口清单

### 5.1 首页模块
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/overview | 获取首页基础统计 |
| GET | /api/v1/homepage/highlights | 获取首页热点数据（热门技术要素、主要国家、Top院校） |

### 5.2 技术要素模块
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/tech-elements | 获取技术要素列表 |
| GET | /api/v1/tech-elements/{id} | 获取技术要素详情 |
| GET | /api/v1/tech-elements/{id}/countries | 获取国家分布 |
| GET | /api/v1/tech-elements/{id}/schools | 获取院校分布 |
| GET | /api/v1/tech-elements/{id}/talents | 获取人才明细 |

### 5.2 国家院校模块
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/country-school/overview | 获取概要统计 |
| GET | /api/v1/country-school/schools | 获取院校分布 |
| GET | /api/v1/country-school/tech-elements | 获取技术要素分布 |
| GET | /api/v1/country-school/talents | 获取人才明细 |

### 5.3 采集配置模块
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/collect/tech-elements | 获取技术要素配置列表 |
| PUT | /api/v1/collect/tech-elements/{id}/sources | 更新采集源配置 |
| POST | /api/v1/collect/tasks | 触发采集任务 |
| GET | /api/v1/collect/tasks | 获取任务列表 |
| GET | /api/v1/collect/tasks/{id} | 获取任务详情 |
| POST | /api/v1/collect/tasks/{id}/cancel | 取消任务 |

### 5.4 数据版本模块
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/data-versions | 获取版本列表 |
| POST | /api/v1/data-versions/{id}/publish | 发布版本 |
| POST | /api/v1/data-versions/{id}/rollback | 回滚版本 |
| GET | /api/v1/data-versions/quality | 获取质量摘要 |

### 5.5 人才池模块
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/talent-pools | 获取人才池列表 |
| POST | /api/v1/talent-pools | 创建人才池 |
| POST | /api/v1/talent-pools/{id}/members | 添加成员 |
| DELETE | /api/v1/talent-pools/{id}/members/{talent_id} | 移除成员 |

---

## 6. 前端页面清单

| 页面 | 路由 | 文件 | 说明 |
|------|------|------|------|
| 首页 | / | HomePage.tsx | 双主视角概要 |
| 技术要素 | /tech-element | TechElementPage.tsx | 业务部门主视角 |
| 国家院校 | /country-school | CountrySchoolPage.tsx | 平台部门主视角（院校机构） |
| 人才搜索 | /search | SearchPage.tsx | 跨视角检索 |
| 人才详情 | /talent/:id | TalentDetailPage.tsx | 人才详情页 |
| 学校详情 | /school/:id | SchoolDetailPage.tsx | 学校详情页 |
| 我的收藏 | /favorites | FavoritesPage.tsx | 轻量运营收口 |
| 权限管理 | /admin | AdminPage.tsx | 用户权限配置 |
| 采集配置 | /collect | CollectPage.tsx | 采集配置管理 |
| 数据版本 | /data-version | DataVersionPage.tsx | 版本发布管理 |

---

## 7. 任务包完成状态

| 任务包 | 名称 | 状态 |
|--------|------|------|
| TP1 | 信息架构与导航升级 | ✅ 已完成 |
| TP2 | 首页主视角概要区 | ✅ 已完成 |
| TP3 | 技术要素页面 | ✅ 已完成 |
| TP4 | 国家院校页面 | ✅ 已完成 |
| TP5 | 搜索增强与详情增强 | ✅ 已完成 |
| TP6 | 收藏与人才池闭环 | ✅ 已完成 |
| TP7 | 权限扩展 | ✅ 已完成 |
| TP8 | 采集配置与任务管理 | ✅ 已完成 |
| TP9 | 版本发布与数据质量 | ✅ 已完成 |
| TP10 | 联调测试与验收收口 | ✅ 已完成 |

---

## 8. 不纳入范围（明确边界）

| 不纳入项 | 说明 |
|----------|------|
| ATS 深度对接 | 不对接招聘流程系统 |
| 智能推荐引擎 | 不做自动推荐排序 |
| 学院/实验室主链路 | 不做学院级别页面 |
| 多数据源融合 | 仅使用 OpenAlex |
| 高复杂 BI 分析 | 不做大屏分析 |
| 订阅推送告警 | 不做消息推送 |
| 自动发布机制 | 发布需人工确认 |

---

## 9. 文档依据

| 文档编号 | 文档名称 |
|----------|----------|
| 31 | MVP v1.1 变更需求清单（CR List） |
| 32 | MVP v1.1 范围边界与版本说明 |
| 06B | 需求规格说明书（MVP v1.1） |
| 33 | 第二轮开发任务包与迭代 Backlog |
| 34 | MVP v1.1 测试增补清单 |
| 采集配置管理使用说明 | 开发过程新增文档 |

---

## 10. 核心页面数据呈现逻辑

### 10.1 首页数据呈现逻辑

#### 10.1.1 数据来源

| 数据区域 | API 端点 | 数据来源表 |
|----------|----------|-----------|
| 基础统计 | `GET /api/v1/overview` | core_school, core_talent (聚合统计表) |
| 技术要素统计 | 沿用 overview 返回 | stats 对象 |
| 热点标签 | `GET /api/v1/homepage/highlights` | 数据库实时查询 |

#### 10.1.2 呈现逻辑

**基础统计区（6个统计卡片）**：
```
数据流：overview API → stats 对象 → 6个 Statistic 组件

字段映射：
- school_count     → 已收录院校机构
- professor_count  → 教授类人才
- student_count    → 学生类人才
- talent_count     → 总人才数
- tech_element_count → 技术要素
- country_count    → 覆盖国家
```

**双主视角概要卡**：

| 卡片 | 展示指标 | 数据来源 |
|------|----------|----------|
| 技术要素概要卡 | 技术要素数、技术方向数、人才总数、覆盖国家、覆盖院校 | stats 对象 |
| 国家院校概要卡 | 覆盖国家、覆盖院校、人才总数、覆盖技术要素、技术方向 | stats 对象 |

**热点标签区**：
- 热门技术要素：API返回 `hot_tech_elements`（Top6，按人才数排序）
- 主要国家：API返回 `top_countries`（Top5，按人才数排序）
- Top院校机构：API返回 `top_schools`（Top5，按人才数排序）

#### 10.1.3 交互逻辑

| 交互 | 动作 |
|------|------|
| 搜索框输入 | 输入关键词 → 回车/点击搜索 → 跳转到 `/search?q=关键词` |
| 技术要素标签点击 | 跳转到 `/tech-element?tech_element={id}` |
| 国家标签点击 | 跳转到 `/country-school?country_id={id}` |
| 院校标签点击 | 跳转到 `/country-school?school_id={id}` |
| "进入"按钮点击 | 跳转到对应主视角页面 |

---

### 10.2 技术要素页面数据呈现逻辑

#### 10.2.1 数据来源

| API 端点 | 说明 | 后端实现 |
|----------|------|----------|
| `GET /api/v1/tech-elements` | 技术要素列表 | TechElementRepository.get_all_elements() |
| `GET /api/v1/tech-elements/overall-stats` | 总体统计 | TechElementRepository.get_overall_stats() |
| `GET /api/v1/tech-elements/overall-talents` | 总体人才列表 | TechElementRepository.get_talent_list() |
| `GET /api/v1/tech-elements/{id}/stats` | 筛选后统计 | TechElementRepository.get_element_stats(id) |
| `GET /api/v1/tech-elements/{id}/talents` | 筛选后人才 | TechElementRepository.get_talent_list(element_id) |

#### 10.2.2 数据查询逻辑

**总体统计查询**（get_overall_stats）：

```sql
-- 人才总数（基于 TalentTechTag 关联）
SELECT COUNT(DISTINCT talent_id)
FROM TalentTechTag
WHERE is_enabled = True

-- 教授数
SELECT COUNT(DISTINCT talent_id)
FROM TalentTechTag
JOIN Talent ON TalentTechTag.talent_id = Talent.talent_id
WHERE TalentTechTag.is_enabled = True
  AND Talent.role_type = 'professor'

-- 学生数
SELECT COUNT(DISTINCT talent_id)
FROM TalentTechTag
JOIN Talent ON TalentTechTag.talent_id = Talent.talent_id
WHERE TalentTechTag.is_enabled = True
  AND Talent.role_type IN ('student', 'graduated')

-- 覆盖国家数
SELECT COUNT(DISTINCT Country.country_id)
FROM TalentTechTag
JOIN Talent ON TalentTechTag.talent_id = Talent.talent_id
JOIN School ON Talent.school_id = School.school_id
JOIN Country ON School.country_id = Country.country_id
WHERE TalentTechTag.is_enabled = True

-- 覆盖院校数、技术要素数、技术方向数（类似关联查询）
```

**核心设计原则**：
1. 所有统计基于 `TalentTechTag` 表关联
2. 启用过滤条件：`TalentTechTag.is_enabled == True`
3. 去重统计使用 `COUNT(DISTINCT ...)`
4. 多表关联：TalentTechTag → Talent → School → Country

#### 10.2.3 呈现逻辑

**页面初始化流程**：
```
1. 加载技术要素列表 → techElements
2. 加载总体统计 → overallStats
3. 加载总体人才列表 → talentData (分页)
```

**筛选条件变化流程**：
```
选择技术要素 → 重置技术方向 → 更新统计 → 更新人才列表
选择技术方向 → 更新统计 → 更新人才列表
其他筛选 → 点击查询 → 更新人才列表
```

**概要统计区展示**：
| 指标 | 数据来源 |
|------|----------|
| 人才总数 | overallStats.talent_count |
| 教授/科研人员 | overallStats.professor_count |
| 学生 | overallStats.student_count |
| 覆盖院校 | overallStats.school_count |
| 覆盖国家 | overallStats.country_count |
| 技术方向 | overallStats.tech_direction_count |

**人才列表字段**：
| 列 | 字段 | 说明 |
|----|------|------|
| 姓名 | name | 点击跳转详情页 |
| 学校 | school_name | 关联 School 表 |
| 角色 | role_type | professor/student/graduated/unknown |
| H指数 | h_index | 支持排序 |
| 论文数 | works_count | 支持排序 |
| 技术方向 | topic_tags | 标签展示，最多3个 |

#### 10.2.4 设计特点

1. **总体优先**：默认显示用户权限范围内所有有技术标签的人才
2. **筛选可选**：不强制选择技术要素，可按国家/学校/角色筛选
3. **联动逻辑**：选择技术要素后，技术方向下拉才可用

---

### 10.3 院校机构页面数据呈现逻辑

#### 10.3.1 数据来源

| API 端点 | 说明 | 后端实现 |
|----------|------|----------|
| `GET /api/v1/overview` | 总体统计 | StatisticsRepository |
| `GET /api/v1/countries` | 国家列表 | countries list |
| `GET /api/v1/schools` | 学校列表 | schools list |

#### 10.3.2 区域定义

```javascript
const REGIONS = {
  north_america: {
    name: '北美地区',
    countries: ['US', 'CA']
  },
  asia_pacific: {
    name: '亚太地区',
    countries: ['CN', 'JP', 'KR', 'SG', 'AU', 'NZ', 'HK', 'TW', 'IN', 'MY', 'TH']
  },
  europe: {
    name: '欧洲地区',
    countries: ['GB', 'DE', 'FR', 'CH', 'NL', 'IT', 'ES', 'SE', 'AT', 'BE', 'DK', 'FI', 'NO', 'IE', 'PT', 'PL']
  },
  other: {
    name: '其他',
    countries: [] // 动态计算：有人才的国家 - 已定义区域国家
  }
}
```

**排序顺序**：北美地区 → 亚太地区 → 欧洲地区 → 其他

**其他区域逻辑**：
- 不属于北美/亚太/欧洲的国家自动归入"其他"
- 例如：以色列(IL)、巴西(BR)、南非(ZA)等国家

#### 10.3.3 呈现逻辑

**页面初始化流程**：
```
1. 加载国家列表 → countries
2. 加载总体统计 → summary (从 overview API)
3. 加载学校列表 → schools
4. 默认显示北美地区 Tab
```

**数据过滤逻辑**：
```javascript
// 前端过滤
filteredSchools = schools
  .filter(s => currentRegionCountries.includes(s.country_code))  // 按区域
  .filter(s => countryId ? s.country_code === selectedCountryCode : true)  // 按国家
  .filter(s => keyword ? s.school_name.includes(keyword) : true)  // 按关键词
  .sort((a, b) => (b.professor_count + b.student_count) - (a.professor_count + a.student_count))  // 按人才数排序
```

**概要统计区展示**：
| 指标 | 数据来源 |
|------|----------|
| 人才总数 | overview.stats.talent_count |
| 教授/科研人员 | overview.stats.professor_count |
| 学生 | overview.stats.student_count |
| 覆盖院校 | overview.stats.school_count |

**院校列表字段**：
| 列 | 字段 | 说明 |
|----|------|------|
| 院校 | school_name | 点击跳转学校详情页 |
| 国家 | country_name | - |
| 教授/科研人员 | professor_count | 支持排序 |
| 学生 | student_count | 支持排序 |

#### 10.3.4 设计特点

1. **区域 Tab 导航**：北美/亚太/欧洲/其他四个区域 Tab，便于用户快速切换
2. **前端过滤**：学校列表一次性加载，筛选在前端执行
3. **人才数排序**：默认按教授数+学生数降序排列
4. **Tab 标签显示数量**：每个区域 Tab 显示该区域院校数量
5. **完整区域覆盖**："其他"区域确保所有国家都有归属

---

### 10.4 数据呈现逻辑总结

#### 10.4.1 权限过滤原则

| 页面 | 权限过滤方式 | 说明 |
|------|--------------|------|
| 首页 | 后端过滤 | overview API 已按用户权限范围统计 |
| 技术要素页 | 后端过滤 | 所有查询基于 TalentTechTag 关联，支持权限扩展 |
| Top院校页 | 后端过滤 | schools API 已按用户权限范围返回 |

#### 10.4.2 数据一致性保证

1. **统计口径一致**：所有统计基于相同的数据模型关联
2. **去重统计**：使用 `COUNT(DISTINCT ...)` 避免重复计数
3. **分页一致**：列表和统计使用相同的过滤条件

#### 10.4.3 待优化项

| 项目 | 当前状态 | 优化建议 |
|------|----------|----------|
| 技术要素页国家/学校下拉 | 未加载选项数据 | 补充 API 调用加载国家/学校列表 |
| 院校机构页技术要素分布 | 未实现 | 补充按技术要素统计的人才分布 Tab |

---

## 11. 版本冻结结论

本文件作为 MVP v1.1 最终需求版本依据，总结了原始 CR 清单和开发过程中优化新增的需求。v1.1 版本已全部完成开发并通过验收。
