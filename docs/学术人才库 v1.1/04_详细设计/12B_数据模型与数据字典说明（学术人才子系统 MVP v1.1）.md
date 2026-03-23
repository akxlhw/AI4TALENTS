# 12B_数据模型与数据字典说明（学术人才子系统 MVP v1.1）

**文档名称**：数据模型与数据字典说明（学术人才子系统 MVP v1.1）  
**文档编号**：12B  
**版本**：V1.0  
**状态**：冻结版  
**适用范围**：智能人才库—学术人才子系统 MVP v1.1

---

## 1. 文档目标

本文件用于冻结 v1.1 的关键业务对象、对象关系、核心字段和状态口径。重点解决：

- 技术要素 / 技术方向如何建模
- 人才与技术标签如何关联
- 收藏 / 人才池 / 备注 / 跟进状态如何建模
- 采集范围 / 采集策略 / 采集任务 / 数据版本如何建模
- 状态值如何统一并与前端页面、接口 DTO 保持一致

本文件是数据库详细设计、接口设计、页面字段冻结表和测试设计的重要上游输入。

---

## 2. 数据模型总览

### 2.1 分层
建议按四层组织：

#### 基础主数据层
- region
- country
- school
- talent

#### 业务分析层
- tech_element
- tech_direction
- tech_direction_mapping
- talent_tech_tag

#### 运营层
- favorite
- talent_pool
- talent_pool_member
- talent_note
- followup_record

#### 数据运营层
- collection_scope
- sync_policy
- sync_job
- data_version
- publish_record
- manual_correction_log
- data_quality_snapshot

### 2.2 核心关系
- 一个区域包含多个国家
- 一个国家包含多个学校
- 一个学校包含多个人才
- 一个技术要素包含多个技术方向
- 一个技术方向可映射多个外部主题
- 一个人才可关联多个技术标签
- 一个用户可收藏多个人才
- 一个用户可拥有多个自定义人才池
- 一个采集策略可对应多次采集任务
- 一个时间点只能存在一个当前生效数据版本

---

## 3. 基础主数据对象

### 3.1 区域（region）

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint/uuid | 是 | 主键 |
| region_code | varchar | 是 | 区域编码 |
| region_name | varchar | 是 | 区域名称 |
| region_name_en | varchar | 否 | 英文名称 |
| sort_order | int | 否 | 排序 |
| is_enabled | boolean | 是 | 是否启用 |
| created_at | datetime | 是 | 创建时间 |
| updated_at | datetime | 是 | 更新时间 |

### 3.2 国家（country）

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint/uuid | 是 | 主键 |
| country_code | varchar | 是 | 国家编码 |
| country_name | varchar | 是 | 国家中文名 |
| country_name_en | varchar | 否 | 英文名 |
| region_id | bigint/uuid | 是 | 所属区域 |
| is_enabled | boolean | 是 | 是否启用 |
| created_at | datetime | 是 | 创建时间 |
| updated_at | datetime | 是 | 更新时间 |

### 3.3 学校（school）

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint/uuid | 是 | 主键 |
| school_code | varchar | 否 | 内部编码 |
| school_name | varchar | 是 | 学校名称 |
| school_name_en | varchar | 否 | 英文名 |
| region_id | bigint/uuid | 是 | 所属区域 |
| country_id | bigint/uuid | 是 | 所属国家 |
| school_intro | text | 否 | 学校简介 |
| school_status | varchar | 是 | 学校状态 |
| normalization_status | varchar | 是 | 归一状态 |
| source_ref | varchar | 否 | 源系统引用 |
| is_enabled | boolean | 是 | 是否启用 |
| created_at | datetime | 是 | 创建时间 |
| updated_at | datetime | 是 | 更新时间 |

**school_status**：`active / inactive / hidden`  
**normalization_status**：`normalized / pending_confirm / excluded`

### 3.4 人才（talent）

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint/uuid | 是 | 主键 |
| talent_code | varchar | 否 | 内部编码 |
| full_name | varchar | 是 | 姓名 |
| full_name_en | varchar | 否 | 英文名 |
| current_role | varchar | 是 | 当前角色 |
| role_confirm_status | varchar | 是 | 角色确认状态 |
| school_id | bigint/uuid | 否 | 当前学校 |
| country_id | bigint/uuid | 否 | 当前国家 |
| region_id | bigint/uuid | 否 | 当前区域 |
| is_graduated | boolean | 否 | 是否已毕业 |
| talent_status | varchar | 是 | 人才状态 |
| academic_summary | text | 否 | 学术摘要 |
| recruitment_summary | text | 否 | 招聘摘要 |
| data_completeness_level | varchar | 是 | 数据完整度 |
| display_status | varchar | 是 | 展示状态 |
| source_ref | varchar | 否 | 源数据引用 |
| current_data_version_id | bigint/uuid | 否 | 当前版本 |
| created_at | datetime | 是 | 创建时间 |
| updated_at | datetime | 是 | 更新时间 |

**current_role**：`professor / student / graduated_student / pending_confirm / other`  
**role_confirm_status**：`confirmed / auto_identified / pending_confirm`  
**talent_status**：`active / archived / pending_confirm`  
**data_completeness_level**：`high / medium / low`  
**display_status**：`visible / hidden / excluded`

---

## 4. 技术分类对象

### 4.1 技术要素（tech_element）

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint/uuid | 是 | 主键 |
| element_code | varchar | 是 | 技术要素编码 |
| element_name | varchar | 是 | 技术要素名称 |
| element_desc | text | 否 | 描述 |
| sort_order | int | 否 | 排序 |
| is_enabled | boolean | 是 | 是否启用 |
| created_at | datetime | 是 | 创建时间 |
| updated_at | datetime | 是 | 更新时间 |

### 4.2 技术方向（tech_direction）

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint/uuid | 是 | 主键 |
| direction_code | varchar | 是 | 技术方向编码 |
| direction_name | varchar | 是 | 技术方向名称 |
| tech_element_id | bigint/uuid | 是 | 所属技术要素 |
| direction_desc | text | 否 | 描述 |
| sort_order | int | 否 | 排序 |
| is_enabled | boolean | 是 | 是否启用 |
| created_at | datetime | 是 | 创建时间 |
| updated_at | datetime | 是 | 更新时间 |

### 4.3 技术方向映射（tech_direction_mapping）
用于维护内部技术方向与 OpenAlex concept/topic/subject 的映射。

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint/uuid | 是 | 主键 |
| tech_direction_id | bigint/uuid | 是 | 技术方向 |
| source_type | varchar | 是 | 来源类型 |
| source_key | varchar | 是 | 来源主题标识 |
| source_name | varchar | 是 | 来源主题名称 |
| mapping_type | varchar | 是 | 映射类型 |
| weight | decimal | 否 | 映射权重 |
| is_primary | boolean | 是 | 是否主映射 |
| is_enabled | boolean | 是 | 是否启用 |

**mapping_type**：`primary / secondary / candidate`

### 4.4 人才技术标签（talent_tech_tag）

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint/uuid | 是 | 主键 |
| talent_id | bigint/uuid | 是 | 人才 |
| tech_element_id | bigint/uuid | 是 | 技术要素 |
| tech_direction_id | bigint/uuid | 是 | 技术方向 |
| tag_level | varchar | 是 | 主/次方向 |
| tag_source | varchar | 是 | 标签来源 |
| confirm_status | varchar | 是 | 确认状态 |
| confidence_score | decimal | 否 | 置信度 |
| is_enabled | boolean | 是 | 是否启用 |
| created_at | datetime | 是 | 创建时间 |
| updated_at | datetime | 是 | 更新时间 |

**tag_level**：`primary / secondary`  
**tag_source**：`auto_mapping / manual_adjustment / imported`  
**confirm_status**：`confirmed / auto_identified / pending_confirm`

---

## 5. 运营对象

### 5.1 收藏（favorite）
| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint/uuid | 是 | 主键 |
| user_id | bigint/uuid | 是 | 用户 |
| talent_id | bigint/uuid | 是 | 人才 |
| favorite_status | varchar | 是 | 收藏状态 |
| created_at | datetime | 是 | 创建时间 |
| updated_at | datetime | 是 | 更新时间 |

**favorite_status**：`active / canceled`

### 5.2 人才池（talent_pool）
| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | bigint/uuid | 是 | 主键 |
| pool_name | varchar | 是 | 人才池名称 |
| pool_type | varchar | 否 | 类型 |
| owner_user_id | bigint/uuid | 是 | 所有人 |
| scope_desc | text | 否 | 说明 |
| pool_status | varchar | 是 | 状态 |
| created_at | datetime | 是 | 创建时间 |
| updated_at | datetime | 是 | 更新时间 |

**pool_type**：`tech_element / country / campaign / custom`  
**pool_status**：`active / archived`

### 5.3 人才池成员（talent_pool_member）
- pool_id
- talent_id
- added_by
- created_at

### 5.4 人才备注（talent_note）
- talent_id
- user_id
- note_content
- is_latest
- created_at
- updated_at

### 5.5 跟进记录（followup_record）
- talent_id
- user_id
- followup_status
- followup_comment
- created_at
- updated_at

**followup_status**：
- new_found
- reviewed
- followed
- pending_evaluation
- recommend_contact
- no_followup

---

## 6. 数据运营对象

### 6.1 采集范围（collection_scope）
- scope_type：`country / school / tech_element / tech_direction`
- scope_ref_id
- scope_ref_name
- is_enabled
- remark
- created_by / updated_by
- created_at / updated_at

### 6.2 采集策略（sync_policy）
- policy_name
- schedule_type：`manual / daily / weekly / biweekly / monthly`
- sync_mode：`full / incremental`
- retry_times
- max_batch_size
- rate_limit_value
- timeout_seconds
- is_enabled

### 6.3 采集任务（sync_job）
- job_code
- trigger_type：`manual / schedule`
- sync_mode
- scope_snapshot
- job_status：`pending / running / success / partial_success / failed / canceled`
- pulled_count / inserted_count / updated_count / failed_count
- error_summary
- started_at / finished_at

### 6.4 数据版本（data_version）
- version_code
- sync_job_id
- version_status：`generated / verified / published / archived`
- version_summary
- is_current_live
- generated_at / published_at / published_by

### 6.5 发布记录（publish_record）
- data_version_id
- publish_action：`publish / rollback / archive`
- action_user_id
- action_comment
- created_at

### 6.6 人工纠偏记录（manual_correction_log）
- target_type：`talent / school / tech_tag`
- target_id
- correction_type：`role_adjustment / tech_direction_adjustment / display_status_adjustment / pending_confirm_mark`
- before_value / after_value
- correction_reason
- corrected_by
- created_at

### 6.7 数据质量摘要（data_quality_snapshot）
- data_version_id
- normalized_school_count / pending_school_count
- confirmed_role_count / pending_role_count
- confirmed_tech_tag_count / pending_tech_tag_count
- excluded_count
- created_at

---

## 7. 查询与统计口径说明

### 7.1 首页口径
首页摘要和热点标签必须基于：
- 当前生效数据版本
- 当前用户权限范围
- `display_status = visible` 的对象

### 7.2 技术要素页口径
概要统计、国家分布、院校分布和人才明细必须共享同一 Query Context。

### 7.3 国家院校页口径
概要统计、院校分布、技术要素分布和人才明细必须共享同一 Query Context。

### 7.4 搜索口径
搜索页与其他页面共享人才列表 DTO 语义和状态口径，不能出现角色或状态解释差异。

---

## 8. 数据字典使用规则

1. 页面名“技术要素”与字段 `tech_element` 保持一致。  
2. 页面名“国家院校”不是字段名，字段层仍使用 region / country / school。  
3. 核心业务对象尽量采用状态字段和软控制，不建议频繁物理删除。  
4. 审计类对象必须保留创建/更新时间和操作人。  
5. 所有状态值必须与 `26B_页面字段与状态冻结表` 保持一致。

---

## 9. 结论

本文件冻结了 v1.1 的主要业务对象、关键字段、状态口径和统计语义。  
后续数据库详细设计、接口 DTO、页面字段和测试用例设计，均应以本文件为上游依据，不应各自发散。
