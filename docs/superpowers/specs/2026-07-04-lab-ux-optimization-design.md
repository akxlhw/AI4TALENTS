# AI 实验室前端页面与交互优化设计

> 版本：V1.0  
> 日期：2026-07-04  
> 状态：待实施  
> 关联项目：AI4TALENTS 智能人才库 V2.2.0

---

## 1. 背景与目标

### 1.1 当前问题

`domains/lab/` 前端已实现“概览 → 搜索 → 详情”三页面 + 管理员 JSONL 导入 Tab，功能可用但存在以下问题：

- **视觉平庸**：页面偏向默认 Ant Design 样式，缺少数据可视化与域级品牌感。
- **信息层次弱**：统计卡片平铺、筛选栏拥挤、人才卡片信息垂直堆叠、详情页像表单。
- **交互缺失**：无排序、无重置、URL 不同步页码、返回按钮行为僵化、研究方向存在 `&nbsp` 未解码。
- **技术栈滞后**：Lab 页面仍使用 `useState/useEffect` 手动管理请求，未接入项目选定的 React Query + Zustand。

### 1.2 优化目标

- 提升实验室域的视觉品质与信息可读性，使其与学术/开源域达到同一水准。
- 重构交互流程，减少用户操作成本。
- 对齐技术栈，消除技术债，为后续功能扩展打好基础。

### 1.3 范围边界

**包含：**

- `frontend/src/pages/lab/` 下三个页面（概览、搜索、详情）。
- `frontend/src/pages/system-config/components/lab-import-tab.tsx` 视觉与交互优化。
- Lab 域状态管理 Store、URL 同步逻辑、新增/复用组件。
- 单元测试补充。

**不包含：**

- 收藏 / 对比 / 人才池功能（本次不做，后续迭代）。
- 后端 API 改动（复用现有 `/lab/*` 接口）。

---

## 2. 设计原则

1. **招聘场景优先**：卡片与详情首先展示“是谁、什么身份、属于哪个实验室”。
2. **信息层级清晰**：标题 > 数据 > 辅助信息，通过字号、字重、颜色区分。
3. **科技感但不浮夸**：深蓝 Hero + 清爽内容区，避免过度渐变和阴影。
4. **一致性**：遵循 Ant Design v5 设计系统，复用项目已有组件模式。
5. **响应式优先**：所有布局在移动端可正常浏览。

---

## 3. 信息架构

Lab 域保持 3 个页面 + 1 个系统配置 Tab：

| 路由 | 页面 | 说明 |
|---|---|---|
| `/lab` | 概览页 | 数据仪表板 + 快捷入口 |
| `/lab/search` | 搜索列表页 | 多条件筛选 + 人才网格 |
| `/lab/talents/:talentId` | 详情页 | 人才画像 |
| `/system-config` → 采集配置 → AI 实验室人才导入 | 导入 Tab | 管理员 JSONL 导入 |

新增全局元素：

- **面包屑**：`实验室 / 搜索` → `实验室 / 人才详情 / 周志华`
- **域主题自动应用**：进入 `/lab/*` 路由自动注入 lab 主题 CSS 变量，解决直接刷新时主题色丢失问题。
- **骨架屏**：所有页面主内容区加载时显示骨架屏。
- **统一空状态**：数据为空或搜索无结果时显示插画 + 文案 + 操作按钮。

---

## 4. 视觉设计系统

### 4.1 色彩

沿用 Lab 域已有主题色并强化应用：

| Token | 值 | 用途 |
|---|---|---|
| `--lab-primary` | `#0D2B4E` | Hero 背景、Primary 按钮、关键图标 |
| `--lab-secondary` | `#0EA5E9` | 图表高亮、链接、Hover 态 |
| `--lab-bg` | `#F8FAFC` | 内容区背景 |
| `--lab-card-bg` | `#FFFFFF` | 卡片背景 |
| `--lab-primary-10` | `rgba(13, 43, 78, 0.1)` | 图标背景、轻强调 |

移除硬编码角色颜色（如 `#e94560`），改用 Ant Design token 结合 lab 主题派生色。

### 4.2 卡片

- 圆角：`border-radius: 12px`
- 阴影：`box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06)`，Hover 时加深并微抬升。
- 边框：默认 1px `#F0F0F0`，Hover 时变为主题色 20% 透明度。

### 4.3 图表

使用 ECharts，配色绑定 lab 主题：

- 主色 `#0D2B4E`
- 辅色 `#0EA5E9`
- 辅助色 `#60A5FA`、`#93C5FD`、`#BFDBFE`

---

## 5. 页面设计

### 5.1 概览页（`/lab`）

#### 5.1.1 页面结构（从上到下）

1. **Hero 区**
   - 深蓝渐变背景：`linear-gradient(135deg, #0D2B4E 0%, #0EA5E9 100%)`
   - 左侧：大标题 `AI 实验室人才库` + 副标题 `汇聚全球顶尖 AI 实验室的研究人才`
   - 右侧：实验室/科研装饰图标（轻量，不干扰）
   - 底部：快捷操作栏
     - `浏览全部人才` 主按钮（跳转 `/lab/search`）
     - `导入数据` 按钮（管理员可见，跳转 `/system-config?tab=lab-import`）

2. **统计卡片区**
   - 3 张卡片横向排列：`xs=24 sm=8`
   - 每张卡片内容：
     - 左侧图标（人才/实验室/研究组），背景使用主题色 10% 透明度
     - 右侧：数字（大号字重）+ 标签

3. **数据图表区**
   - 左：`实验室分布` 横向条形图
     - X 轴：人数
     - Y 轴：实验室名称
     - 点击条形跳转 `/lab/search?parent_lab=xxx`
   - 右：`角色分布` 环形图（donut）
     - 分类：教授 / 学生 / 毕业生
     - 中间显示总人数
     - 点击图例触发搜索过滤

4. **学位与热门研究组**
   - 左：`学位层次` 迷你柱状图或分段进度条
   - 右：`热门研究组` 可点击 Tag 云，Tag 可按人数缩放（可选）

5. **页脚信息**
   - 数据来源说明 + 最近采集时间

#### 5.1.2 空状态

- 无数据时显示插画 + 标题 `暂无实验室人才数据`
- 管理员：显示 `去导入` 按钮
- 普通用户：显示 `查看文档` 链接

#### 5.1.3 交互

- 图表元素可点击，点击后跳转搜索页并携带对应筛选参数。
- 统计卡片 Hover 微抬升 + 阴影加深。
- 页面加载显示骨架屏。

---

### 5.2 搜索页（`/lab/search`）

#### 5.2.1 筛选栏

**第一行（核心筛选，始终显示）**

| 控件 | 类型 | 说明 |
|---|---|---|
| 姓名关键词 | Input | 占位符 `输入姓名关键词...`，带搜索图标 |
| 角色 | Select | 选项：全部 / 教授 / 学生 / 毕业生 |
| 学位层次 | Select | 选项：全部 / 博士 / 硕士 / 本科 |
| 排序 | Select | 选项：默认 / 姓名升序 / 届别降序 / 最近创建 |
| 重置 | Button | 清空所有筛选并回到第 1 页 |

**第二行（高级筛选，默认折叠）**

- 展开按钮：`高级筛选 ▼`
- 展开后显示：
  - 顶级实验室：Input
  - 研究组：Input
  - 研究方向：多选 Tag / Select（后端 API 已支持 `research_area`）

#### 5.2.2 人才卡片

布局响应式：

| 断点 | 每行卡片数 |
|---|---|
| ≥1200px | 4 |
| ≥992px | 3 |
| ≥576px | 2 |
| <576px | 1 |

卡片内容：

- 顶部：
  - 头像占位：72px 圆形，无 `photo_url` 时显示姓名首字母 + 主题色背景
  - 姓名（加粗）
  - 角色 Tag + 学位 Tag
- 中部：
  - 顶级实验室 / 研究组 / 当前头衔（最多一行，超出截断）
- 底部：
  - 最多 2 行研究方向 Tag
  - 超出显示 `+N`
  - 修复 `&nbsp` 等 HTML 实体未解码问题

#### 5.2.3 结果区

- 顶部显示 `共 N 条结果`
- 人才网格
- 底部居中分页
- 空状态：插画 + `未找到匹配人才` + `清除筛选` 按钮

#### 5.2.4 交互

- 修改筛选条件自动重置到第 1 页。
- URL query 同步所有筛选条件和页码，刷新后状态不丢失。
- 卡片 Hover：阴影加深 + 边框变为主题色。
- 点击卡片跳转详情页。

---

### 5.3 详情页（`/lab/talents/:talentId`）

#### 5.3.1 页面结构

- **面包屑**：`实验室 / 搜索` → `实验室 / 人才详情 / 周志华`
- **返回按钮**：使用 `navigate(-1)`，支持从任意入口返回

**左右分栏**

- 左栏（宽度 320px，小屏自动堆叠到底部或顶部）：
  - 头像：120px 圆形，无 `photo_url` 时显示姓名首字母 + 主题渐变背景
  - 姓名（level 3）
  - 角色 Tag + 学位 Tag
  - 当前头衔
  - 联系方式：
    - 邮箱（mailto 链接）
    - 个人主页外链按钮
- 右栏：
  - **信息卡**：
    - 顶级实验室
    - 研究组
    - 院系
    - 入学/加入年份
    - 数据来源
    - 采集时间
  - **研究方向卡**：
    - Tag 云
    - 超过 6 个时显示 `展开 / 收起`

#### 5.3.2 空状态

- `talentId` 不存在或加载失败时显示 404 空状态：
  - 标题 `人才不存在或已删除`
  - 按钮 `返回搜索页`

---

### 5.4 导入 Tab（`/system-config` → 采集配置 → AI 实验室人才导入）

#### 5.4.1 页面结构

1. **说明卡片**
   - 标题 `AI 实验室人才导入`
   - 数据格式说明
   - 示例 JSONL 下载链接

2. **表单区**
   - 实验室名称：Input（必填）
   - 文件上传：Dragger，仅接受 `.jsonl`
   - `开始导入` 按钮（未填实验室或未选文件时禁用）

3. **结果报告**（导入成功后显示）
   - 统计：总行数 / 成功解析 / 写入 / 跳过
   - 跳过原因 Alert 列表（最多显示前 50 条，可折叠）

#### 5.4.2 交互

- `beforeUpload` 拦截，手动控制上传时机。
- 导入成功后清空文件，防止重复点击。
- 使用 lab 主题色，移除突兀的 `orange` Tag。

---

## 6. 组件设计

### 6.1 新增/复用组件

| 组件 | 位置 | 说明 |
|---|---|---|
| `LabHero` | `pages/lab/components/lab-hero.tsx` | 概览页 Hero 区 |
| `LabStatCard` | `pages/lab/components/lab-stat-card.tsx` | 统计卡片 |
| `RoleDistributionChart` | `pages/lab/components/role-distribution-chart.tsx` | 角色分布环形图 |
| `LabDistributionChart` | `pages/lab/components/lab-distribution-chart.tsx` | 实验室分布条形图 |
| `LabSearchFilter` | `pages/lab/components/lab-search-filter.tsx` | 搜索筛选栏 |
| `LabTalentCard` | `pages/lab/components/lab-talent-card.tsx` | 人才卡片 |
| `LabTalentHeader` | `pages/lab/components/lab-talent-header.tsx` | 详情页左栏头部 |
| `LabImportForm` | `pages/system-config/components/lab-import-form.tsx` | 导入表单（从现有 Tab 抽取） |
| `EmptyPlaceholder` | `components/empty-placeholder.tsx` | 统一空状态（如不存在则新增） |
| `PageSkeleton` | `components/page-skeleton.tsx` | 统一骨架屏（如不存在则新增） |
| `BreadcrumbNav` | `components/breadcrumb-nav.tsx` | 统一面包屑（如不存在则新增） |

### 6.2 组件拆分原则

- 每个组件单一职责，便于单元测试。
- 组件只接收 props 或读取 Store，不直接调用 API。
- 图表组件通过 `onFilter` 回调与页面交互，不依赖路由。

---

## 7. 数据流与状态管理

### 7.1 React Query Hooks

```text
frontend/src/hooks/lab/
├── useLabStats.ts
├── useLabTalents.ts
└── useLabTalent.ts
```

- `useLabStats()`：获取概览页统计数据，`staleTime: 60s`。
- `useLabTalents(params)`：获取搜索列表，`placeholderData: keepPreviousData`，翻页时保持旧数据。
- `useLabTalent(id)`：获取人才详情，`retry: 1`，404 时不重试。

### 7.2 Zustand Store

```text
frontend/src/stores/labSearchStore.ts
```

状态字段：

- `keyword: string`
- `parentLab: string`
- `labName: string`
- `roleType: string`
- `academicLevel: string`
- `researchArea: string[]`
- `sortBy: 'default' | 'name_asc' | 'cohort_desc' | 'created_desc'`
- `page: number`
- `pageSize: number`
- `advancedOpen: boolean`

核心方法：

- `setFilter(key, value)`：设置筛选条件并自动重置 page=1。
- `resetFilters()`：清空所有筛选。
- `toggleAdvanced()`：切换高级筛选展开状态。
- `syncFromUrl(query)`：从 URL query 恢复状态。
- `toQuery()`：导出为 API / URL query 对象。

### 7.3 URL 同步

搜索页使用 `useEffect` 监听 Store 变化，通过 `setSearchParams` 同步到 URL。

初始化时从 URL 恢复状态到 Store。

### 7.4 主题注入

在 `LabOverviewPage`、`LabSearchPage`、`LabTalentDetailPage` 的 `useEffect` 中调用 `applyDomainCssVars('lab')`。

如果 `MainLayout` 已经通过路由自动设置 domain，则页面级调用作为兜底。

---

## 8. 响应式设计

### 8.1 断点策略

沿用项目已有断点：

| 断点 | 宽度 |
|---|---|
| xs | <576px |
| sm | ≥576px |
| md | ≥768px |
| lg | ≥992px |
| xl | ≥1200px |

### 8.2 关键适配

- **概览页**：
  - Hero 区小屏改为上下布局。
  - 统计卡片小屏单列。
  - 图表区小屏堆叠为单列。

- **搜索页**：
  - 筛选栏小屏全部堆叠为单列。
  - 人才卡片小屏 1-2 列。

- **详情页**：
  - 小屏改为单栏，左栏头像与信息放在顶部。

---

## 9. 错误处理与空状态

### 9.1 错误处理

| 场景 | 处理 |
|---|---|
| API 请求失败 | 页面顶部显示 Alert，提供“重试”按钮 |
| 详情页 talentId 不存在 | 显示 404 空状态，提供“返回搜索页” |
| 网络中断 | React Query 自动重试 1 次，仍失败显示错误 |

### 9.2 空状态

| 页面 | 空状态文案 | 操作 |
|---|---|---|
| 概览页 | 暂无实验室人才数据 | 管理员：去导入；普通用户：查看文档 |
| 搜索页 | 未找到匹配人才 | 清除筛选 |
| 详情页 | 人才不存在或已删除 | 返回搜索页 |

---

## 10. 测试策略

### 10.1 单元测试（Vitest + @testing-library/react）

新增测试文件：

```text
frontend/src/pages/lab/components/__tests__/
├── lab-stat-card.test.tsx
├── lab-search-filter.test.tsx
├── lab-talent-card.test.tsx
└── lab-talent-header.test.tsx

frontend/src/stores/__tests__/
└── labSearchStore.test.ts
```

测试覆盖点：

- 统计卡片正确渲染数字和图标。
- 筛选栏修改条件时调用正确的回调。
- 人才卡片正确截断研究方向并显示 `+N`。
- Store 的 URL 序列化/反序列化正确。
- Store `setFilter` 自动重置 page=1。

### 10.2 E2E 测试（Playwright）

可选补充：

- 从概览页点击“浏览全部人才”进入搜索页。
- 搜索页筛选后 URL 同步。
- 点击人才卡片进入详情页。

---

## 11. 实施风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| 现有 lab 页面代码改动量大 | 可能引入回归 | 按页面逐个重构，每页完成后运行 Vitest 与 Playwright |
| React Query 与现有全局状态冲突 | 数据不一致 | 仅在 lab 域使用新的 Store，不影响其他域 |
| ECharts 在响应式下尺寸异常 | 图表显示异常 | 使用 `resize` 事件监听，或复用项目已有图表容器模式 |
| 后端 `research_area` 筛选项数据格式不确定 | 前端实现困难 | 先实现单选 Input，确认 API 返回后再改为多选 |

---

## 12. 验收标准

- [ ] 概览页包含 Hero、统计卡片、角色环形图、实验室条形图、热门研究组。
- [ ] 搜索页包含核心筛选、高级筛选、排序、重置、人才卡片网格、URL 同步。
- [ ] 详情页采用左右分栏，包含头像占位、角色学位、联系方式、研究方向。
- [ ] 导入页包含说明卡片、结果报告、成功后清空文件。
- [ ] Lab 三页均使用 React Query + Zustand。
- [ ] 所有页面有骨架屏和统一空状态。
- [ ] 新增/修改的组件有单元测试覆盖。
- [ ] `make lint-frontend` 与 `npm run test` 通过。

---

## 13. 附录

### 13.1 相关文件

- `frontend/src/pages/lab/lab-overview-page.tsx`
- `frontend/src/pages/lab/lab-search-page.tsx`
- `frontend/src/pages/lab/lab-talent-detail-page.tsx`
- `frontend/src/pages/system-config/components/lab-import-tab.tsx`
- `frontend/src/services/api/lab.ts`
- `frontend/src/theme/index.ts`
- `frontend/src/stores/domainStore.ts`

### 13.2 参考截图

当前效果截图保存在 `outputs/screenshots/`：

- `lab-overview-page.png`
- `lab-search-page.png`
- `lab-detail-page.png`
