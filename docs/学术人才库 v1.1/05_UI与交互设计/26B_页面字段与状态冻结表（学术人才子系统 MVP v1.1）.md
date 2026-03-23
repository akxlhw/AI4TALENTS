# 26B_页面字段与状态冻结表（学术人才子系统 MVP v1.1）

**文档名称**：页面字段与状态冻结表（学术人才子系统 MVP v1.1）  
**文档编号**：26B  
**版本**：V1.0  
**状态**：冻结版  
**适用范围**：智能人才库—学术人才子系统 MVP v1.1

---

## 1. 文档目标

本文件用于冻结 v1.1 核心页面的：
- 展示字段
- 筛选字段
- 操作字段
- 状态字段
- 状态值

其目的在于避免在前后端实现、联调和测试过程中出现字段漂移和状态口径不一致的问题。

---

## 2. 页面字段冻结

### 2.1 首页

#### 展示字段
- 已收录高校数
- 教授类人才数
- 学生类人才数
- 总人才数
- 授权学校数
- 数据版本
- 数据更新时间
- 技术要素数
- 技术方向数
- 覆盖国家数
- 覆盖院校数
- 覆盖技术要素数
- 热门技术要素标签
- 重点国家标签
- 重点院校标签

#### 操作字段
- 关键词
- 进入技术要素
- 进入国家院校
- 热门技术要素标签点击
- 重点国家标签点击
- 重点院校标签点击

### 2.2 技术要素页

#### 筛选字段
- 技术要素
- 技术方向
- 关键词
- 国家
- 学校
- 人才角色
- 是否已毕业
- 待确认状态

#### 概要统计字段
- 人才总数
- 教授数
- 学生数
- 覆盖国家数
- 覆盖院校数

#### 国家分布字段
- 国家名称
- 人才数
- 教授数
- 学生数
- 占比

#### 院校分布字段
- 院校名称
- 国家名称
- 人才数
- 教授数
- 学生数

#### 人才明细字段
- 姓名
- 当前角色
- 学校
- 国家
- 技术要素
- 技术方向
- 是否已毕业
- 数据完整度
- 招聘摘要
- 收藏状态
- 跟进状态

### 2.3 国家院校页

#### 筛选字段
- 区域
- 国家
- 学校
- 技术要素
- 技术方向
- 关键词
- 人才角色

#### 概要统计字段
- 人才总数
- 教授数
- 学生数
- 覆盖院校数
- 覆盖技术要素数

#### 院校分布字段
- 院校名称
- 国家名称
- 人才数
- 教授数
- 学生数

#### 技术要素分布字段
- 技术要素名称
- 技术方向数
- 人才数
- 教授数
- 学生数

#### 人才明细字段
与技术要素页一致。

### 2.4 搜索页

#### 筛选字段
- 关键词
- 技术要素
- 技术方向
- 区域
- 国家
- 学校
- 人才角色
- 是否已毕业
- 待确认状态

#### 结果字段
- 姓名
- 当前角色
- 学校
- 国家
- 技术要素
- 技术方向
- 是否已毕业
- 数据完整度
- 招聘摘要
- 收藏状态
- 跟进状态
- 更新时间

### 2.5 人才详情页

#### 展示字段
- 姓名
- 英文名
- 当前角色
- 学校
- 国家
- 技术要素列表
- 技术方向列表
- 主方向
- 次方向
- 学术摘要
- 招聘摘要
- 代表成果
- 数据完整度
- 待确认项
- 收藏状态
- 当前跟进状态

#### 操作字段
- 收藏 / 取消收藏
- 加入人才池
- 备注内容
- 跟进状态

### 2.6 我的收藏页
#### 展示字段
- 姓名
- 当前角色
- 学校
- 国家
- 技术要素
- 技术方向
- 跟进状态
- 更新时间
- 收藏状态

#### 操作字段
- 取消收藏
- 加入人才池
- 编辑备注
- 更新跟进状态

### 2.7 后台页面字段

#### 采集范围配置页
- 范围类型
- 范围名称
- 启用状态
- 备注
- 修改时间
- 修改人

#### 采集策略配置页
- 策略名称
- 调度周期
- 采集模式
- 重试次数
- 单批次上限
- 限流参数
- 超时阈值
- 启用状态
- 修改时间
- 修改人

#### 采集任务管理页
- 任务编号
- 触发方式
- 采集模式
- 状态
- 拉取数
- 新增数
- 更新数
- 失败数
- 开始时间
- 结束时间
- 错误摘要

#### 数据版本与发布页
- 版本号
- 版本状态
- 是否当前生效
- 生成时间
- 发布时间
- 版本摘要

#### 数据质量与轻量纠偏页
- 已归一学校数
- 待确认学校数
- 已确认角色数
- 待确认角色数
- 已确认技术标签数
- 待确认技术标签数
- 排除展示数

---

## 3. 状态字段冻结

### 3.1 人才相关状态

#### current_role
- professor
- student
- graduated_student
- pending_confirm
- other

#### role_confirm_status
- confirmed
- auto_identified
- pending_confirm

#### data_completeness_level
- high
- medium
- low

#### display_status
- visible
- hidden
- excluded

### 3.2 技术标签状态

#### tag_level
- primary
- secondary

#### tag_source
- auto_mapping
- manual_adjustment
- imported

#### confirm_status
- confirmed
- auto_identified
- pending_confirm

### 3.3 运营状态

#### favorite_status
- active
- canceled

#### followup_status
- new_found
- reviewed
- followed
- pending_evaluation
- recommend_contact
- no_followup

#### pool_status
- active
- archived

### 3.4 采集与版本状态

#### schedule_type
- manual
- daily
- weekly
- biweekly
- monthly

#### sync_mode
- full
- incremental

#### job_status
- pending
- running
- success
- partial_success
- failed
- canceled

#### version_status
- generated
- verified
- published
- archived

#### publish_action
- publish
- rollback
- archive

### 3.5 学校与归一状态

#### school_status
- active
- inactive
- hidden

#### normalization_status
- normalized
- pending_confirm
- excluded

---

## 4. 状态变更原则

1. `display_status=excluded` 的对象不得在前台展示。  
2. `role_confirm_status=pending_confirm` 的对象可展示，但需提示待确认。  
3. `version_status=generated/verified` 不代表前台已经切换版本。  
4. 只有 `published + is_current_live=true` 的版本才是前台当前生效版本。  
5. 收藏取消建议保留记录，不直接物理删除。  
6. 跟进状态建议保留留痕，页面展示最新状态。  
7. 纠偏动作必须记录修正前值和修正后值。

---

## 5. 结论

本文件是 v1.1 页面字段与状态的冻结依据。  
后续页面实现、接口 DTO、测试用例、状态显示和权限裁剪均必须以本文件为准。
