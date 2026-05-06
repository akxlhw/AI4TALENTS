# MVP v1.2 版本规划

## 1. 版本概述

### 1.1 版本定位

**MVP v1.2 = v1.1 + 技术债务清理 + 架构优化 + 测试补全**

基于 v1.1 发布评估结果（综合评分 7.9/10），v1.2 聚焦于提升代码质量和系统健壮性，而非新增业务功能。

### 1.2 版本目标

| 维度 | v1.1 评分 | v1.2 目标 | 提升 |
|------|----------|----------|------|
| 后端架构 | 8.5/10 | 9.0/10 | +0.5 |
| 前端架构 | 7.5/10 | 8.5/10 | +1.0 |
| 测试覆盖 | 8.0/10 | 9.0/10 | +1.0 |
| 文档完整性 | 7.5/10 | 8.5/10 | +1.0 |
| **综合评分** | **7.9/10** | **8.8/10** | **+0.9** |

---

## 2. 需求清单（CR List）

### 2.1 P0 必须完成（6项）

| 编号 | 变更项 | 说明 | 状态 |
|------|--------|------|------|
| CR-01 | 前端废弃文件清理 | 删除 `*Refactored.tsx` 文件，统一类型定义 | ✅ 已完成 |
| CR-02 | 前端通用组件抽象 | 创建 `TalentTableBase`, `PageHeader`, `FilterSection` | ✅ 已完成 |
| CR-03 | 前端状态管理优化 | 使用 Zustand 统一管理全局状态 | ✅ 已完成 |
| CR-04 | 后端限流中间件 | 添加 API 级别请求限流 (100 req/min) | ✅ 已完成 |
| CR-05 | 后端日志系统配置 | 统一日志格式、添加请求追踪 | ✅ 已完成 |
| CR-06 | 核心API测试补充 | search, talents API 测试 | ✅ 已完成 |

### 2.2 P1 建议完成（5项）

| 编号 | 变更项 | 说明 | 状态 |
|------|--------|------|------|
| CR-07 | 前端常量统一 | 提取 `followupStatusMap` 等常量到 `constants/` | ✅ 已完成 |
| CR-08 | 后端请求日志中间件 | 记录请求路径、响应时间、状态码 | ✅ 已完成 |
| CR-09 | 服务层依赖注入优化 | Endpoint → Service → Repository 统一依赖注入 | ⏳ 未完成 |
| CR-10 | 前端E2E测试补充 | TechElement, CountrySchool, TalentDetail 页面 | ⏳ 未完成 |
| CR-11 | API文档完善 | 添加请求/响应示例 | ⏳ 未完成 |

---

## 3. 任务包规划

### TP1: 前端代码清理与重构 ✅

**目标**: 清理技术债务，提升代码质量

| 任务 | 说明 | 预估 | 状态 |
|------|------|------|------|
| 1.1 删除废弃文件 | 删除 `FavoritesPageRefactored.tsx`, `CollectPageRefactored.tsx` | 0.5h | ✅ |
| 1.2 类型定义统一 | 修复 ID 类型不一致，移除重复定义 | 2h | ✅ |
| 1.3 常量提取 | 创建 `constants/` 目录，提取公共常量 | 1h | ✅ |
| 1.4 页面类型提取 | 将内联类型提取到 `types/index.ts` | 1h | ✅ |

**关键文件**:
- `frontend/src/pages/FavoritesPageRefactored.tsx` - 已删除
- `frontend/src/pages/CollectPageRefactored.tsx` - 已删除
- `frontend/src/types/index.ts` - 统一类型
- `frontend/src/constants/` - 新建常量目录

---

### TP2: 前端通用组件抽象 ✅

**目标**: 减少代码重复，提升组件复用率

| 任务 | 说明 | 预估 | 状态 |
|------|------|------|------|
| 2.1 PageHeader 组件 | 页面标题、图标、操作区统一组件 | 1h | ✅ |
| 2.2 FilterSection 组件 | 筛选区域统一布局和交互 | 2h | ✅ |
| 2.3 SelectionActions 组件 | 批量选择操作栏统一组件 | 1h | ✅ |

**新建文件**:
- `frontend/src/components/common/PageHeader.tsx` ✅
- `frontend/src/components/common/FilterSection.tsx` ✅
- `frontend/src/components/common/SelectionActions.tsx` ✅
- `frontend/src/components/common/index.ts` ✅

---

### TP3: 前端状态管理优化 ✅

**目标**: 使用 Zustand 统一状态管理

| 任务 | 说明 | 预估 | 状态 |
|------|------|------|------|
| 3.1 创建 authStore | 替换 AuthContext | 2h | ✅ |
| 3.2 创建 favoritesStore | 替换 FavoritesContext | 2h | ✅ |
| 3.3 创建 settingsStore | 管理列配置、搜索模板 | 2h | ✅ |

**新建文件**:
- `frontend/src/store/index.ts` ✅
- `frontend/src/store/authStore.ts` ✅
- `frontend/src/store/favoritesStore.ts` ✅
- `frontend/src/store/settingsStore.ts` ✅

**注意**: 保留 Context 文件作为备选，组件迁移可逐步进行

---

### TP4: 后端限流与日志 ✅

**目标**: 提升系统稳定性和可观测性

| 任务 | 说明 | 预估 | 状态 |
|------|------|------|------|
| 4.1 添加限流中间件 | 实现滑动窗口限流 | 2h | ✅ |
| 4.2 配置日志系统 | dictConfig 配置，JSON 格式输出 | 2h | ✅ |
| 4.3 请求日志中间件 | 记录请求路径、响应时间、状态码 | 2h | ✅ |
| 4.4 全局异常处理 | 统一错误响应格式 | 1h | ✅ |

**修改文件**:
- `backend/app/main.py` - 添加中间件 ✅
- `backend/app/core/logging_config.py` - 新建日志配置 ✅
- `backend/app/core/config.py` - 添加限流配置 ✅
- `backend/app/middleware/rate_limit.py` - 新建限流中间件 ✅
- `backend/app/middleware/request_logging.py` - 新建请求日志中间件 ✅

---

### TP5: 测试覆盖补充 ✅

**目标**: 提升测试覆盖率

| 任务 | 说明 | 预估 | 状态 |
|------|------|------|------|
| 5.1 search API 测试 | `test_search.py` | 2h | ✅ |
| 5.2 talents API 测试 | `test_talents.py` | 2h | ✅ |

**测试结果**:
- 后端测试: 236 passed (从 222 增加)

---

### TP6: 文档完善 ✅

**目标**: 提升文档完整性

| 任务 | 说明 | 预估 | 状态 |
|------|------|------|------|
| 6.1 部署文档 | 生产环境部署步骤 | 2h | ✅ |
| 6.2 更新 README | 更新版本信息、v1.2变更说明 | 1h | ✅ |

**新建文件**:
- `docs/部署文档.md` ✅

---

## 4. 工期估算

| 任务包 | 预估工期 | 实际完成 |
|--------|----------|----------|
| TP1: 前端代码清理 | 0.5 天 | ✅ |
| TP2: 通用组件抽象 | 0.5 天 | ✅ |
| TP3: 状态管理优化 | 0.5 天 | ✅ |
| TP4: 后端限流与日志 | 0.5 天 | ✅ |
| TP5: 测试覆盖补充 | 0.5 天 | ✅ |
| TP6: 文档完善 | 0.5 天 | ✅ |

**总工期**: 约 3 天

---

## 5. 验收标准

### 5.1 前端验收

| 指标 | 标准 | 状态 |
|------|------|------|
| 废弃文件 | 无 `*Refactored.tsx` 文件 | ✅ |
| 类型一致性 | 所有 ID 类型为 `number` | ✅ |
| 常量统一 | 公共常量在 `constants/` 目录 | ✅ |
| 状态管理 | Zustand stores 已创建 | ✅ |

### 5.2 后端验收

| 指标 | 标准 | 状态 |
|------|------|------|
| 限流配置 | 所有 API 限流 100 req/min | ✅ |
| 日志格式 | JSON 结构化日志 | ✅ |
| 请求追踪 | 所有请求有 request_id | ✅ |

### 5.3 测试验收

| 指标 | 标准 | 状态 |
|------|------|------|
| 后端测试 | 236 tests passed | ✅ |
| 前端构建 | 构建成功 | ✅ |

---

## 6. 风险与依赖

### 6.1 技术风险

| 风险 | 影响 | 缓解措施 | 状态 |
|------|------|----------|------|
| Zustand 迁移兼容性 | 中 | 保留 Context 作为备选 | ✅ 已缓解 |
| 限流影响正常用户 | 低 | 配置合理的限流阈值 | ✅ 已缓解 |
| 测试环境限流干扰 | 中 | 测试环境禁用限流 | ✅ 已解决 |

### 6.2 外部依赖

| 依赖 | 说明 | 状态 |
|------|------|------|
| zustand | React 状态管理库 | ✅ 已安装 |
| python-json-logger | Python JSON 日志库 | ✅ 已安装 |

---

## 7. 不纳入范围

| 不纳入项 | 说明 |
|----------|------|
| Redis 缓存层 | v1.3 规划 |
| 性能测试 | v1.3 规划 |
| 安全测试 | v1.3 规划 |
| APM 监控 | v2.0 规划 |
| 新业务功能 | 本版本聚焦技术债务 |

---

## 8. 发布说明

### 版本信息
- **版本号**: v1.2.0
- **发布日期**: 2026-03-30
- **前置版本**: v1.1.0

### 主要变更

1. **前端架构优化**
   - 清理废弃文件，统一类型定义
   - 提取公共常量到 `constants/` 目录
   - 创建可复用的通用组件
   - 引入 Zustand 状态管理

2. **后端稳定性提升**
   - 新增 API 限流中间件
   - 统一 JSON 结构化日志
   - 请求追踪 (X-Request-ID)

3. **测试与文档**
   - 新增 search/talents API 测试
   - 新增生产环境部署文档
