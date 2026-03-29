# 28B_接口字段映射与前后端 DTO 清单（学术人才子系统 MVP v1.1）

**文档名称**：接口字段映射与前后端 DTO 清单（学术人才子系统 MVP v1.1）  
**文档编号**：28B  
**版本**：V1.0  
**状态**：冻结版  
**适用范围**：智能人才库—学术人才子系统 MVP v1.1

---

## 1. 文档目标

本文件用于冻结 v1.1 前后端主要接口和 DTO 语义，重点解决：
- 首页概要和热点标签需要什么接口
- 技术要素页和国家院校页怎么组织接口
- 搜索、详情、收藏、后台配置使用什么 DTO
- 各接口应返回哪些字段
- 前端展示字段和内部数据模型如何映射

---

## 2. 接口分组总览

- 首页接口组
- 技术要素接口组
- 国家院校接口组
- 搜索接口组
- 人才详情接口组
- 收藏 / 人才池接口组
- 权限管理接口组
- 采集配置与任务接口组
- 数据版本与质量接口组

---

## 3. 首页接口组

### 3.1 首页基础统计接口
**路径建议**：`GET /api/v1/home/summary`

#### 响应 DTO：HomeSummaryDTO
- schoolCount
- professorCount
- studentCount
- totalTalentCount
- authorizedSchoolCount
- dataVersion
- dataUpdatedAt

### 3.2 首页技术要素概要接口
**路径建议**：`GET /api/v1/home/tech-element-overview`

#### HomeTechElementOverviewDTO
- techElementCount
- techDirectionCount
- totalTalentCount
- countryCount
- schoolCount
- hotTechElements: array<HotTechElementDTO>

#### HotTechElementDTO
- techElementId
- techElementName
- talentCount
- jumpParams

### 3.3 首页国家院校概要接口
**路径建议**：`GET /api/v1/home/country-school-overview`

#### HomeCountrySchoolOverviewDTO
- countryCount
- schoolCount
- totalTalentCount
- techElementCount
- keyCountries: array<KeyCountryDTO>
- keySchools: array<KeySchoolDTO>

#### KeyCountryDTO
- countryId
- countryName
- talentCount
- jumpParams

#### KeySchoolDTO
- schoolId
- schoolName
- countryName
- talentCount
- jumpParams

---

## 4. 技术要素接口组

### 4.1 筛选项接口
**路径建议**：`GET /api/v1/tech-elements/filter-options`

#### TechElementFilterOptionsDTO
- techElements: array<OptionDTO>
- techDirections: array<TechDirectionOptionDTO>
- countries: array<OptionDTO>
- schools: array<OptionDTO>
- roles: array<OptionDTO>

### 4.2 查询请求 DTO：TechElementQueryDTO
- techElementId
- techDirectionId
- keyword
- countryId
- schoolId
- role
- graduated
- pendingConfirmOnly
- pageNo
- pageSize
- sortBy
- sortOrder

### 4.3 概要统计接口
**路径建议**：`GET /api/v1/tech-elements/summary`

#### TechElementSummaryDTO
- totalTalentCount
- professorCount
- studentCount
- countryCount
- schoolCount

### 4.4 国家分布接口
**路径建议**：`GET /api/v1/tech-elements/country-distribution`

#### TechElementCountryDistributionItemDTO
- countryId
- countryName
- talentCount
- professorCount
- studentCount
- ratio
- jumpParams

### 4.5 院校分布接口
**路径建议**：`GET /api/v1/tech-elements/school-distribution`

#### TechElementSchoolDistributionItemDTO
- schoolId
- schoolName
- countryId
- countryName
- talentCount
- professorCount
- studentCount
- jumpParams

### 4.6 人才明细接口
**路径建议**：`GET /api/v1/tech-elements/talents`

#### TalentListPageDTO
- total
- list: array<TalentListItemDTO>
- pageNo
- pageSize
- viewMode

---

## 5. 国家院校接口组

### 5.1 筛选项接口
**路径建议**：`GET /api/v1/country-schools/filter-options`

#### CountrySchoolFilterOptionsDTO
- regions
- countries
- schools
- techElements
- techDirections
- roles

### 5.2 查询请求 DTO：CountrySchoolQueryDTO
- regionId
- countryId
- schoolId
- techElementId
- techDirectionId
- keyword
- role
- pageNo
- pageSize
- sortBy
- sortOrder

### 5.3 概要统计接口
**路径建议**：`GET /api/v1/country-schools/summary`

#### CountrySchoolSummaryDTO
- totalTalentCount
- professorCount
- studentCount
- schoolCount
- techElementCount

### 5.4 院校分布接口
**路径建议**：`GET /api/v1/country-schools/school-distribution`

#### CountrySchoolDistributionItemDTO
- schoolId
- schoolName
- countryId
- countryName
- talentCount
- professorCount
- studentCount
- jumpParams

### 5.5 技术要素分布接口
**路径建议**：`GET /api/v1/country-schools/tech-element-distribution`

#### CountrySchoolTechElementDistributionItemDTO
- techElementId
- techElementName
- techDirectionCount
- talentCount
- professorCount
- studentCount
- jumpParams

### 5.6 人才明细接口
**路径建议**：`GET /api/v1/country-schools/talents`
- 复用 `TalentListPageDTO`

---

## 6. 搜索接口组

### 6.1 搜索请求 DTO：TalentSearchQueryDTO
- keyword
- techElementId
- techDirectionId
- regionId
- countryId
- schoolId
- role
- graduated
- pendingConfirmOnly
- sortBy
- sortOrder
- pageNo
- pageSize

### 6.2 搜索接口
**路径建议**：`GET /api/v1/talents/search`

#### TalentListItemDTO
- talentId
- fullName
- currentRole
- currentRoleLabel
- schoolId
- schoolName
- countryId
- countryName
- techElements
- techDirections
- isGraduated
- followupStatus
- isFavorited
- dataCompletenessLevel
- recruitmentSummary
- updatedAt

---

## 7. 人才详情接口组

### 7.1 详情接口
**路径建议**：`GET /api/v1/talents/{talentId}`

#### TalentDetailDTO
- talentId
- fullName
- fullNameEn
- currentRole
- currentRoleLabel
- schoolId
- schoolName
- countryId
- countryName
- techElementList
- techDirectionList
- primaryDirection
- secondaryDirections
- academicSummary
- recruitmentSummary
- representativeWorks
- dataCompletenessLevel
- pendingItems
- isFavorited
- currentFollowupStatus

---

## 8. 收藏 / 人才池接口组

### 8.1 收藏
- `POST /api/v1/favorites`
- `DELETE /api/v1/favorites/{talentId}`
- `GET /api/v1/favorites`

#### FavoriteCreateDTO
- talentId

### 8.2 人才池
- `POST /api/v1/talent-pools`
- `GET /api/v1/talent-pools`
- `POST /api/v1/talent-pools/{poolId}/members`

#### TalentPoolCreateDTO
- poolName
- poolType
- scopeDesc

#### TalentPoolListItemDTO
- poolId
- poolName
- poolType
- memberCount
- updatedAt

#### TalentPoolAddMemberDTO
- talentId

### 8.3 备注与跟进
- `POST /api/v1/talents/{talentId}/notes`
- `POST /api/v1/talents/{talentId}/followup`

#### TalentNoteCreateDTO
- noteContent

#### FollowupUpdateDTO
- followupStatus
- comment

---

## 9. 权限管理接口组

### 9.1 用户权限详情
**路径建议**：`GET /api/v1/admin/users/{userId}/permissions`

#### UserPermissionDTO
- userId
- roleCodes
- allowedSchoolIds
- allowedCountryIds
- allowedTechElementIds
- defaultView

### 9.2 用户权限保存
**路径建议**：`POST /api/v1/admin/users/{userId}/permissions`

#### UserPermissionUpdateDTO
- roleCodes
- allowedSchoolIds
- allowedCountryIds
- allowedTechElementIds
- defaultView

---

## 10. 采集配置与任务接口组

### 10.1 采集范围
- `GET /api/v1/admin/collection-scopes`
- `POST /api/v1/admin/collection-scopes`

#### CollectionScopeListItemDTO
- scopeId
- scopeType
- scopeRefId
- scopeRefName
- isEnabled
- remark
- updatedAt
- updatedBy

#### CollectionScopeSaveDTO
- scopeType
- scopeRefId
- isEnabled
- remark

### 10.2 采集策略
- `GET /api/v1/admin/sync-policies`
- `POST /api/v1/admin/sync-policies`

#### SyncPolicySaveDTO
- policyName
- scheduleType
- syncMode
- retryTimes
- maxBatchSize
- rateLimitValue
- timeoutSeconds
- isEnabled

### 10.3 手动触发任务
- `POST /api/v1/admin/sync-jobs/trigger`

#### SyncJobTriggerDTO
- syncMode
- policyId
- remark

### 10.4 任务列表
- `GET /api/v1/admin/sync-jobs`

#### SyncJobListItemDTO
- jobId
- jobCode
- triggerType
- syncMode
- jobStatus
- pulledCount
- insertedCount
- updatedCount
- failedCount
- startedAt
- finishedAt
- errorSummary

---

## 11. 数据版本与质量接口组

### 11.1 版本列表
- `GET /api/v1/admin/data-versions`

#### DataVersionListItemDTO
- versionId
- versionCode
- versionStatus
- isCurrentLive
- generatedAt
- publishedAt
- versionSummary

### 11.2 发布版本
- `POST /api/v1/admin/data-versions/{versionId}/publish`

#### PublishVersionDTO
- comment

### 11.3 质量摘要
- `GET /api/v1/admin/data-versions/{versionId}/quality-summary`

#### DataQualitySummaryDTO
- normalizedSchoolCount
- pendingSchoolCount
- confirmedRoleCount
- pendingRoleCount
- confirmedTechTagCount
- pendingTechTagCount
- excludedCount

---

## 12. 通用 DTO 与映射要求

### 12.1 OptionDTO
- value
- label

### 12.2 映射要求
- DTO 应优先服务页面语义，不直接暴露源字段结构
- 状态值与 26B 一致
- 页面展示名与内部码值分离
- 跳转参数建议后端构造并返回

### 12.3 权限要求
所有接口必须在后端自动附加权限边界，前端即使不传相关条件，也不能返回越权结果。

---

## 13. 结论

本文件冻结了 v1.1 的主要接口组和前后端 DTO 口径。  
后续 Swagger、联调和测试时应以本文件为接口语义基线，避免出现页面字段和接口字段各自漂移的情况。
