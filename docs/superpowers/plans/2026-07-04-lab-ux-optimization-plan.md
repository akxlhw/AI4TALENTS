# AI 实验室前端页面与交互优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 AI 实验室（Lab）域的前端页面从 MVP 级别重构为与学术/开源域同等级别的生产级页面：统一 Lab 主题、接入 React Query + Zustand、新增数据可视化、优化三页一 Tab 的交互与视觉，并补充单元测试。

**Architecture:** 以 React Query 负责服务端数据获取与缓存，Zustand 负责搜索页客户端状态与 URL 同步，组件按功能拆分到 `pages/lab/components/`，新增/复用全局空状态、骨架屏、面包屑组件。ECharts 负责概览页图表。

**Tech Stack:** React 18 + TypeScript + Vite + Ant Design v5 + TanStack React Query v5 + Zustand + ECharts + echarts-for-react + Vitest + @testing-library/react

---

## 文件结构

### 新增文件

| 文件 | 用途 |
|---|---|
| `frontend/src/hooks/useLabQueries.ts` | Lab 域 React Query hooks |
| `frontend/src/stores/labSearchStore.ts` | 搜索页状态 + URL 同步 |
| `frontend/src/components/EmptyPlaceholder.tsx` | 统一空状态组件 |
| `frontend/src/components/PageSkeleton.tsx` | 统一页面骨架屏 |
| `frontend/src/components/BreadcrumbNav.tsx` | 统一面包屑组件 |
| `frontend/src/pages/lab/components/lab-hero.tsx` | 概览页 Hero 区 |
| `frontend/src/pages/lab/components/lab-stat-card.tsx` | 概览页统计卡片 |
| `frontend/src/pages/lab/components/role-distribution-chart.tsx` | 角色分布环形图 |
| `frontend/src/pages/lab/components/lab-distribution-chart.tsx` | 实验室分布横向条形图 |
| `frontend/src/pages/lab/components/lab-search-filter.tsx` | 搜索筛选栏 |
| `frontend/src/pages/lab/components/lab-talent-card.tsx` | 人才卡片 |
| `frontend/src/pages/lab/components/lab-talent-header.tsx` | 详情页头部左栏 |
| `frontend/src/pages/lab/components/lab-import-form.tsx` | 导入表单（从 Tab 抽取） |
| `frontend/src/pages/lab/components/__tests__/lab-stat-card.test.tsx` | 统计卡片测试 |
| `frontend/src/pages/lab/components/__tests__/lab-search-filter.test.tsx` | 筛选栏测试 |
| `frontend/src/pages/lab/components/__tests__/lab-talent-card.test.tsx` | 人才卡片测试 |
| `frontend/src/pages/lab/components/__tests__/lab-talent-header.test.tsx` | 详情头部测试 |
| `frontend/src/stores/__tests__/labSearchStore.test.ts` | Store 测试 |

### 修改文件

| 文件 | 修改内容 |
|---|---|
| `frontend/src/hooks/queryClient.ts` | 增加 lab query keys |
| `frontend/src/hooks/index.ts` | 导出 lab hooks |
| `frontend/src/pages/lab/lab-overview-page.tsx` | 使用新组件 + React Query |
| `frontend/src/pages/lab/lab-search-page.tsx` | 使用新组件 + React Query + Zustand |
| `frontend/src/pages/lab/lab-talent-detail-page.tsx` | 使用新组件 + React Query + 左右分栏 |
| `frontend/src/pages/system-config/components/lab-import-tab.tsx` | 使用 LabImportForm + 主题色 |

---

## Task 1：扩展 React Query query keys 与 lab hooks

**Files:**
- Modify: `frontend/src/hooks/queryClient.ts`
- Create: `frontend/src/hooks/useLabQueries.ts`
- Modify: `frontend/src/hooks/index.ts`
- Test: `frontend/src/hooks/__tests__/useLabQueries.test.ts`（可选，Task 10 统一验证）

**依赖说明：** `api.lab` 已存在，无需改动。`LabStats`、`LabTalent`、`LabTalentDetail`、`PaginatedResponse` 类型已存在。

- [ ] **Step 1：在 queryClient.ts 增加 lab query keys**

Open `frontend/src/hooks/queryClient.ts`, add inside `queryKeys` object after `collect`:

```typescript
  // Lab
  lab: {
    stats: ['lab', 'stats'] as const,
    talents: (params?: object) => ['lab', 'talents', params] as const,
    talent: (id: number) => ['lab', 'talent', id] as const,
  },
```

- [ ] **Step 2：创建 useLabQueries.ts**

Create `frontend/src/hooks/useLabQueries.ts`:

```typescript
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import { queryKeys, staleTimes } from './queryClient'
import type { LabStats, LabTalent, LabTalentDetail } from '../types'
import type { PaginatedResponse } from '../types'

export function useLabStats() {
  return useQuery({
    queryKey: queryKeys.lab.stats,
    queryFn: async () => {
      const response = await api.lab.getStats()
      return response.data as LabStats
    },
    staleTime: staleTimes.stats,
  })
}

export interface LabTalentSearchParams {
  keyword?: string
  parent_lab?: string
  lab_name?: string
  role_type?: string
  academic_level?: string
  research_area?: string
  sort_by?: string
  page?: number
  page_size?: number
}

export function useLabTalents(params?: LabTalentSearchParams) {
  return useQuery({
    queryKey: queryKeys.lab.talents(params),
    queryFn: async () => {
      const response = await api.lab.listTalents(params as Record<string, unknown>)
      return response.data as PaginatedResponse<LabTalent>
    },
    staleTime: staleTimes.list,
    placeholderData: (previousData) => previousData,
  })
}

export function useLabTalent(id?: number) {
  return useQuery({
    queryKey: queryKeys.lab.talent(id ?? 0),
    queryFn: async () => {
      const response = await api.lab.getTalent(id!)
      return response.data as LabTalentDetail
    },
    staleTime: staleTimes.detail,
    enabled: !!id,
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404) return false
      return failureCount < 1
    },
  })
}
```

- [ ] **Step 3：在 hooks/index.ts 导出 lab hooks**

Open `frontend/src/hooks/index.ts`, append:

```typescript
export * from './useLabQueries'
```

- [ ] **Step 4：运行 type-check 确保无类型错误**

Run: `cd frontend && npm run type-check`

Expected: pass with no errors.

- [ ] **Step 5：Commit**

```bash
cd D:/AI/AI4TALENT
git add frontend/src/hooks/queryClient.ts frontend/src/hooks/useLabQueries.ts frontend/src/hooks/index.ts
git commit -m "feat(lab): add React Query hooks and query keys for lab domain"
```

---

## Task 2：创建 labSearchStore 及单元测试

**Files:**
- Create: `frontend/src/stores/labSearchStore.ts`
- Create: `frontend/src/stores/__tests__/labSearchStore.test.ts`

**依赖说明：** Zustand 已安装。

- [ ] **Step 1：创建 labSearchStore.ts**

Create `frontend/src/stores/labSearchStore.ts`:

```typescript
import { create } from 'zustand'

export interface LabSearchState {
  keyword: string
  parentLab: string
  labName: string
  roleType: string
  academicLevel: string
  researchArea: string
  sortBy: 'default' | 'name_asc' | 'cohort_desc' | 'created_desc'
  page: number
  pageSize: number
  advancedOpen: boolean

  setFilter: <K extends keyof Omit<LabSearchState, 'setFilter' | 'resetFilters' | 'toggleAdvanced' | 'syncFromUrl' | 'toQuery'>>(
    key: K,
    value: LabSearchState[K]
  ) => void
  resetFilters: () => void
  toggleAdvanced: () => void
  syncFromUrl: (query: URLSearchParams) => void
  toQuery: () => Record<string, string>
}

const initialState: Omit<LabSearchState, 'setFilter' | 'resetFilters' | 'toggleAdvanced' | 'syncFromUrl' | 'toQuery'> = {
  keyword: '',
  parentLab: '',
  labName: '',
  roleType: '',
  academicLevel: '',
  researchArea: '',
  sortBy: 'default',
  page: 1,
  pageSize: 20,
  advancedOpen: false,
}

export const useLabSearchStore = create<LabSearchState>((set, get) => ({
  ...initialState,

  setFilter: (key, value) => {
    set({ [key]: value, page: 1 })
  },

  resetFilters: () => {
    set({ ...initialState })
  },

  toggleAdvanced: () => {
    set((state) => ({ advancedOpen: !state.advancedOpen }))
  },

  syncFromUrl: (query) => {
    set({
      keyword: query.get('keyword') || '',
      parentLab: query.get('parent_lab') || '',
      labName: query.get('lab_name') || '',
      roleType: query.get('role_type') || '',
      academicLevel: query.get('academic_level') || '',
      researchArea: query.get('research_area') || '',
      sortBy: (query.get('sort_by') as LabSearchState['sortBy']) || 'default',
      page: parseInt(query.get('page') || '1', 10),
      pageSize: parseInt(query.get('page_size') || '20', 10),
      advancedOpen: query.has('advanced') && query.get('advanced') === '1',
    })
  },

  toQuery: () => {
    const state = get()
    const query: Record<string, string> = {}
    if (state.keyword) query.keyword = state.keyword
    if (state.parentLab) query.parent_lab = state.parentLab
    if (state.labName) query.lab_name = state.labName
    if (state.roleType) query.role_type = state.roleType
    if (state.academicLevel) query.academic_level = state.academicLevel
    if (state.researchArea) query.research_area = state.researchArea
    if (state.sortBy !== 'default') query.sort_by = state.sortBy
    if (state.page > 1) query.page = String(state.page)
    if (state.pageSize !== 20) query.page_size = String(state.pageSize)
    if (state.advancedOpen) query.advanced = '1'
    return query
  },
}))
```

- [ ] **Step 2：创建 Store 单元测试**

Create `frontend/src/stores/__tests__/labSearchStore.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { useLabSearchStore } from '../labSearchStore'

describe('labSearchStore', () => {
  beforeEach(() => {
    useLabSearchStore.setState(useLabSearchStore.getInitialState())
  })

  it('should initialize with default values', () => {
    const state = useLabSearchStore.getState()
    expect(state.keyword).toBe('')
    expect(state.page).toBe(1)
    expect(state.sortBy).toBe('default')
  })

  it('should set filter and reset page to 1', () => {
    useLabSearchStore.getState().setFilter('page', 3)
    useLabSearchStore.getState().setFilter('keyword', '周')
    const state = useLabSearchStore.getState()
    expect(state.keyword).toBe('周')
    expect(state.page).toBe(1)
  })

  it('should reset filters to defaults', () => {
    useLabSearchStore.getState().setFilter('keyword', '周')
    useLabSearchStore.getState().setFilter('page', 3)
    useLabSearchStore.getState().resetFilters()
    const state = useLabSearchStore.getState()
    expect(state.keyword).toBe('')
    expect(state.page).toBe(1)
  })

  it('should sync from URL params', () => {
    const query = new URLSearchParams('keyword=周&role_type=professor&page=2&sort_by=name_asc')
    useLabSearchStore.getState().syncFromUrl(query)
    const state = useLabSearchStore.getState()
    expect(state.keyword).toBe('周')
    expect(state.roleType).toBe('professor')
    expect(state.page).toBe(2)
    expect(state.sortBy).toBe('name_asc')
  })

  it('should convert state to query object', () => {
    useLabSearchStore.setState({
      keyword: '周',
      roleType: 'professor',
      page: 2,
      sortBy: 'name_asc',
    })
    const query = useLabSearchStore.getState().toQuery()
    expect(query).toEqual({
      keyword: '周',
      role_type: 'professor',
      page: '2',
      sort_by: 'name_asc',
    })
  })
})
```

- [ ] **Step 3：运行 Store 测试**

Run: `cd frontend && npx vitest run src/stores/__tests__/labSearchStore.test.ts`

Expected: all tests pass.

- [ ] **Step 4：Commit**

```bash
cd D:/AI/AI4TALENT
git add frontend/src/stores/labSearchStore.ts frontend/src/stores/__tests__/labSearchStore.test.ts
git commit -m "feat(lab): add lab search store with URL sync and tests"
```

---

## Task 3：创建通用组件（空状态、骨架屏、面包屑）

**Files:**
- Create: `frontend/src/components/EmptyPlaceholder.tsx`
- Create: `frontend/src/components/PageSkeleton.tsx`
- Create: `frontend/src/components/BreadcrumbNav.tsx`

**依赖说明：** Ant Design 已安装。

- [ ] **Step 1：创建 EmptyPlaceholder.tsx**

Create `frontend/src/components/EmptyPlaceholder.tsx`:

```typescript
import { Empty, Button, Space, Typography } from 'antd'

const { Text, Title } = Typography

interface EmptyPlaceholderProps {
  title?: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
}

const EmptyPlaceholder: React.FC<EmptyPlaceholderProps> = ({
  title = '暂无数据',
  description,
  action,
}) => {
  return (
    <Empty
      style={{ padding: 48 }}
      description={
        <Space direction="vertical" size={8}>
          <Title level={5} style={{ margin: 0 }}>
            {title}
          </Title>
          {description && <Text type="secondary">{description}</Text>}
          {action && <Button type="primary" onClick={action.onClick}>{action.label}</Button>}
        </Space>
      }
    />
  )
}

export default EmptyPlaceholder
```

- [ ] **Step 2：创建 PageSkeleton.tsx**

Create `frontend/src/components/PageSkeleton.tsx`:

```typescript
import { Skeleton, Card, Row, Col } from 'antd'

const PageSkeleton: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Skeleton active paragraph={{ rows: 0 }} title={{ width: 300 }} />
      <Row gutter={16} style={{ marginTop: 24 }}>
        {[1, 2, 3].map((i) => (
          <Col xs={24} sm={8} key={i}>
            <Card>
              <Skeleton active avatar paragraph={{ rows: 1 }} />
            </Card>
          </Col>
        ))}
      </Row>
      <Card style={{ marginTop: 24 }}>
        <Skeleton active paragraph={{ rows: 6 }} />
      </Card>
    </div>
  )
}

export default PageSkeleton
```

- [ ] **Step 3：创建 BreadcrumbNav.tsx**

Create `frontend/src/components/BreadcrumbNav.tsx`:

```typescript
import { Breadcrumb } from 'antd'
import { Link } from 'react-router-dom'

export interface BreadcrumbItem {
  label: string
  path?: string
}

interface BreadcrumbNavProps {
  items: BreadcrumbItem[]
}

const BreadcrumbNav: React.FC<BreadcrumbNavProps> = ({ items }) => {
  return (
    <Breadcrumb style={{ marginBottom: 16 }}>
      {items.map((item, index) => (
        <Breadcrumb.Item key={index}>
          {item.path && index < items.length - 1 ? (
            <Link to={item.path}>{item.label}</Link>
          ) : (
            item.label
          )}
        </Breadcrumb.Item>
      ))}
    </Breadcrumb>
  )
}

export default BreadcrumbNav
```

- [ ] **Step 4：运行 type-check**

Run: `cd frontend && npm run type-check`

Expected: pass.

- [ ] **Step 5：Commit**

```bash
cd D:/AI/AI4TALENT
git add frontend/src/components/EmptyPlaceholder.tsx frontend/src/components/PageSkeleton.tsx frontend/src/components/BreadcrumbNav.tsx
git commit -m "feat(components): add EmptyPlaceholder, PageSkeleton, BreadcrumbNav"
```

---

## Task 4：创建 Lab 业务组件

**Files:**
- Create: `frontend/src/pages/lab/components/lab-hero.tsx`
- Create: `frontend/src/pages/lab/components/lab-stat-card.tsx`
- Create: `frontend/src/pages/lab/components/role-distribution-chart.tsx`
- Create: `frontend/src/pages/lab/components/lab-distribution-chart.tsx`
- Create: `frontend/src/pages/lab/components/lab-search-filter.tsx`
- Create: `frontend/src/pages/lab/components/lab-talent-card.tsx`
- Create: `frontend/src/pages/lab/components/lab-talent-header.tsx`
- Create: `frontend/src/pages/lab/components/lab-import-form.tsx`

**依赖说明：** ECharts、echarts-for-react、Ant Design 已安装。主题变量通过 `var(--domain-*)` 使用。

- [ ] **Step 1：创建 lab-hero.tsx**

Create `frontend/src/pages/lab/components/lab-hero.tsx`:

```typescript
import { useNavigate } from 'react-router-dom'
import { Button, Typography, Space } from 'antd'
import { ExperimentOutlined, ArrowRightOutlined, UploadOutlined } from '@ant-design/icons'
import { useAuth } from '../../../contexts/AuthContext'

const { Title, Paragraph } = Typography

const LabHero: React.FC = () => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdmin = user?.role === 'super_admin'

  return (
    <div
      style={{
        background: 'var(--domain-gradient)',
        padding: '64px 32px 48px',
        color: '#fff',
        position: 'relative',
        overflow: 'hidden',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.06,
          backgroundImage: 'radial-gradient(circle at 2px 2px, rgba(255,255,255,0.8) 1px, transparent 0)',
          backgroundSize: '28px 28px',
        }}
      />
      <div style={{ position: 'relative', zIndex: 1, maxWidth: 800, margin: '0 auto' }}>
        <Title level={1} style={{ color: '#fff', margin: 0, marginBottom: 12, fontWeight: 800 }}>
          <ExperimentOutlined style={{ marginRight: 12 }} />
          AI 实验室人才库
        </Title>
        <Paragraph style={{ color: 'rgba(255,255,255,0.85)', fontSize: 16, marginBottom: 32 }}>
          汇聚全球顶尖 AI 实验室的研究人才
        </Paragraph>
        <Space size={16}>
          <Button
            type="primary"
            size="large"
            style={{ background: '#fff', color: 'var(--domain-primary)', fontWeight: 600 }}
            icon={<ArrowRightOutlined />}
            onClick={() => navigate('/lab/search')}
          >
            浏览全部人才
          </Button>
          {isAdmin && (
            <Button
              size="large"
              style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', borderColor: 'rgba(255,255,255,0.3)' }}
              icon={<UploadOutlined />}
              onClick={() => navigate('/system-config?tab=lab-import')}
            >
              导入数据
            </Button>
          )}
        </Space>
      </div>
    </div>
  )
}

export default LabHero
```

- [ ] **Step 2：创建 lab-stat-card.tsx**

Create `frontend/src/pages/lab/components/lab-stat-card.tsx`:

```typescript
import { Card, Statistic } from 'antd'
import type { ReactNode } from 'react'

interface LabStatCardProps {
  title: string
  value: number
  icon: ReactNode
}

const LabStatCard: React.FC<LabStatCardProps> = ({ title, value, icon }) => {
  return (
    <Card
      style={{
        height: '100%',
        borderRadius: 12,
        transition: 'all 0.2s ease',
      }}
      bodyStyle={{ display: 'flex', alignItems: 'center', gap: 16 }}
      hoverable
    >
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: 12,
          background: 'var(--domain-light-bg)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 28,
          color: 'var(--domain-primary)',
        }}
      >
        {icon}
      </div>
      <Statistic title={title} value={value} valueStyle={{ fontSize: 32, fontWeight: 700, color: '#1a202c' }} />
    </Card>
  )
}

export default LabStatCard
```

- [ ] **Step 3：创建 role-distribution-chart.tsx**

Create `frontend/src/pages/lab/components/role-distribution-chart.tsx`:

```typescript
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

interface RoleDistributionChartProps {
  data: { name: string; value: number }[]
  onSliceClick?: (name: string) => void
}

const ROLE_COLORS = ['#0D2B4E', '#0EA5E9', '#60A5FA', '#93C5FD']

const RoleDistributionChart: React.FC<RoleDistributionChartProps> = ({ data, onSliceClick }) => {
  const total = data.reduce((sum, item) => sum + item.value, 0)

  const option: EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, left: 'center' },
    color: ROLE_COLORS,
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: {
          label: { show: true, fontSize: 18, fontWeight: 'bold', formatter: `{b}\n{c}` },
        },
        labelLine: { show: false },
        data,
      },
    ],
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '42%',
        style: {
          text: `${total}`,
          textAlign: 'center',
          fill: '#1a202c',
          fontSize: 24,
          fontWeight: 'bold',
        },
      },
      {
        type: 'text',
        left: 'center',
        top: '50%',
        style: { text: '总计', textAlign: 'center', fill: '#718096', fontSize: 12 },
      },
    ],
  }

  const onEvents = {
    click: (params: any) => {
      if (onSliceClick) onSliceClick(params.name)
    },
  }

  return <ReactECharts option={option} style={{ height: 300 }} onEvents={onEvents} />
}

export default RoleDistributionChart
```

- [ ] **Step 4：创建 lab-distribution-chart.tsx**

Create `frontend/src/pages/lab/components/lab-distribution-chart.tsx`:

```typescript
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

interface LabDistributionChartProps {
  data: { name: string; value: number }[]
  onBarClick?: (name: string) => void
}

const LabDistributionChart: React.FC<LabDistributionChartProps> = ({ data, onBarClick }) => {
  const option: EChartsOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: data.map((d) => d.name), inverse: true },
    series: [
      {
        type: 'bar',
        data: data.map((d) => d.value),
        itemStyle: {
          color: 'var(--domain-secondary)',
          borderRadius: [0, 4, 4, 0],
        },
        barWidth: '60%',
      },
    ],
  }

  const onEvents = {
    click: (params: any) => {
      if (onBarClick) onBarClick(params.name)
    },
  }

  return <ReactECharts option={option} style={{ height: Math.max(200, data.length * 40 + 80) }} onEvents={onEvents} />
}

export default LabDistributionChart
```

- [ ] **Step 5：创建 lab-search-filter.tsx**

Create `frontend/src/pages/lab/components/lab-search-filter.tsx`:

```typescript
import { Card, Row, Col, Input, Select, Button, Space } from 'antd'
import { SearchOutlined, FilterOutlined, ReloadOutlined } from '@ant-design/icons'
import type { LabSearchState } from '../../../stores/labSearchStore'

const { Option } = Select

interface LabSearchFilterProps {
  state: LabSearchState
}

const ROLE_OPTIONS = [
  { label: '全部角色', value: '' },
  { label: '教授', value: 'professor' },
  { label: '学生', value: 'student' },
  { label: '博后/研究员', value: 'graduate' },
]

const LEVEL_OPTIONS = [
  { label: '全部学位', value: '' },
  { label: '博士', value: 'phd' },
  { label: '硕士', value: 'master' },
  { label: '学士', value: 'bachelor' },
]

const SORT_OPTIONS = [
  { label: '默认排序', value: 'default' },
  { label: '姓名升序', value: 'name_asc' },
  { label: '届别降序', value: 'cohort_desc' },
  { label: '最近创建', value: 'created_desc' },
]

const LabSearchFilter: React.FC<LabSearchFilterProps> = ({ state }) => {
  return (
    <Card style={{ marginBottom: 16, borderRadius: 12 }}>
      <Row gutter={[16, 16]} align="middle">
        <Col xs={24} sm={12} md={6} lg={5}>
          <Input
            placeholder="输入姓名关键词..."
            prefix={<SearchOutlined />}
            value={state.keyword}
            onChange={(e) => state.setFilter('keyword', e.target.value)}
            allowClear
          />
        </Col>
        <Col xs={12} sm={6} md={4} lg={4}>
          <Select
            placeholder="角色"
            style={{ width: '100%' }}
            value={state.roleType || undefined}
            onChange={(v) => state.setFilter('roleType', v || '')}
            options={ROLE_OPTIONS}
            allowClear
          />
        </Col>
        <Col xs={12} sm={6} md={4} lg={4}>
          <Select
            placeholder="学位层次"
            style={{ width: '100%' }}
            value={state.academicLevel || undefined}
            onChange={(v) => state.setFilter('academicLevel', v || '')}
            options={LEVEL_OPTIONS}
            allowClear
          />
        </Col>
        <Col xs={12} sm={6} md={4} lg={4}>
          <Select
            placeholder="排序"
            style={{ width: '100%' }}
            value={state.sortBy}
            onChange={(v) => state.setFilter('sortBy', v)}
            options={SORT_OPTIONS}
          />
        </Col>
        <Col xs={12} sm={6} md={4} lg={3}>
          <Button icon={<FilterOutlined />} onClick={state.toggleAdvanced}>
            高级筛选
          </Button>
        </Col>
        <Col xs={12} sm={6} md={4} lg={3}>
          <Button icon={<ReloadOutlined />} onClick={state.resetFilters}>
            重置
          </Button>
        </Col>
      </Row>

      {state.advancedOpen && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12} md={8}>
            <Input
              placeholder="顶级实验室"
              value={state.parentLab}
              onChange={(e) => state.setFilter('parentLab', e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Input
              placeholder="研究组"
              value={state.labName}
              onChange={(e) => state.setFilter('labName', e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Input
              placeholder="研究方向"
              value={state.researchArea}
              onChange={(e) => state.setFilter('researchArea', e.target.value)}
              allowClear
            />
          </Col>
        </Row>
      )}
    </Card>
  )
}

export default LabSearchFilter
```

- [ ] **Step 6：创建 lab-talent-card.tsx**

Create `frontend/src/pages/lab/components/lab-talent-card.tsx`:

```typescript
import { Card, Tag, Typography, Space, Avatar } from 'antd'
import { useNavigate } from 'react-router-dom'
import type { LabTalent } from '../../../types'
import { domainThemes } from '../../../theme'

const { Text } = Typography
const dt = domainThemes.lab

const ROLE_LABELS: Record<string, string> = {
  professor: '教授',
  student: '学生',
  graduate: '博后/研究员',
  unknown: '其他',
}

const LEVEL_LABELS: Record<string, string> = {
  phd: '博士',
  master: '硕士',
  bachelor: '学士',
}

interface LabTalentCardProps {
  talent: LabTalent
}

function decodeHtmlEntities(text: string): string {
  const textarea = document.createElement('textarea')
  textarea.innerHTML = text
  return textarea.value
}

const LabTalentCard: React.FC<LabTalentCardProps> = ({ talent }) => {
  const navigate = useNavigate()
  const initials = talent.name.slice(0, 1)

  return (
    <Card
      hoverable
      size="small"
      onClick={() => navigate(`/lab/talents/${talent.talent_id}`)}
      style={{ borderRadius: 12, height: '100%' }}
    >
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Space align="center">
          <Avatar
            size={48}
            src={undefined}
            style={{ background: dt.gradient, color: '#fff', fontWeight: 600 }}
          >
            {initials}
          </Avatar>
          <div>
            <Text strong style={{ fontSize: 16, display: 'block' }}>
              {talent.name}
            </Text>
            <Space size={4} wrap>
              <Tag>{ROLE_LABELS[talent.role_type] || talent.role_type}</Tag>
              {talent.academic_level && (
                <Tag color="blue">{LEVEL_LABELS[talent.academic_level] || talent.academic_level}</Tag>
              )}
            </Space>
          </div>
        </Space>

        <div>
          <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
            {talent.parent_lab}
          </Text>
          {talent.lab_name && talent.lab_name !== talent.parent_lab && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
              {talent.lab_name}
            </Text>
          )}
          {talent.current_title && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
              {talent.current_title}
            </Text>
          )}
        </div>

        {talent.research_areas && talent.research_areas.length > 0 && (
          <Space size={4} wrap style={{ minHeight: 44 }}>
            {talent.research_areas.slice(0, 4).map((area) => (
              <Tag key={area} color="geekblue" style={{ fontSize: 11, maxWidth: 160 }}>
                {decodeHtmlEntities(area)}
              </Tag>
            ))}
            {talent.research_areas.length > 4 && (
              <Tag style={{ fontSize: 11 }}>+{talent.research_areas.length - 4}</Tag>
            )}
          </Space>
        )}
      </Space>
    </Card>
  )
}

export default LabTalentCard
```

- [ ] **Step 7：创建 lab-talent-header.tsx**

Create `frontend/src/pages/lab/components/lab-talent-header.tsx`:

```typescript
import { Avatar, Tag, Typography, Space, Button } from 'antd'
import { MailOutlined, HomeOutlined } from '@ant-design/icons'
import type { LabTalentDetail } from '../../../types'
import { domainThemes } from '../../../theme'

const { Title, Text } = Typography
const dt = domainThemes.lab

const ROLE_LABELS: Record<string, string> = {
  professor: '教授',
  student: '学生',
  graduate: '博后/研究员',
  unknown: '其他',
}

const LEVEL_LABELS: Record<string, string> = {
  phd: '博士',
  master: '硕士',
  bachelor: '学士',
}

interface LabTalentHeaderProps {
  talent: LabTalentDetail
}

const LabTalentHeader: React.FC<LabTalentHeaderProps> = ({ talent }) => {
  const initials = talent.name.slice(0, 1)

  return (
    <div style={{ textAlign: 'center' }}>
      <Avatar
        size={120}
        src={talent.photo_url || undefined}
        style={{ background: dt.gradient, color: '#fff', fontSize: 48, fontWeight: 700, marginBottom: 16 }}
      >
        {initials}
      </Avatar>
      <Title level={3} style={{ marginBottom: 8 }}>
        {talent.name}
      </Title>
      <Space size={8} wrap style={{ justifyContent: 'center', marginBottom: 8 }}>
        <Tag color="processing">{ROLE_LABELS[talent.role_type] || talent.role_type}</Tag>
        {talent.academic_level && (
          <Tag color="blue">{LEVEL_LABELS[talent.academic_level] || talent.academic_level}</Tag>
        )}
      </Space>
      {talent.current_title && (
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          {talent.current_title}
        </Text>
      )}
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {talent.email && (
          <Button icon={<MailOutlined />} href={`mailto:${talent.email}`} block>
            {talent.email}
          </Button>
        )}
        {talent.homepage && (
          <Button icon={<HomeOutlined />} href={talent.homepage} target="_blank" block>
            个人主页
          </Button>
        )}
      </Space>
    </div>
  )
}

export default LabTalentHeader
```

- [ ] **Step 8：创建 lab-import-form.tsx**

Create `frontend/src/pages/lab/components/lab-import-form.tsx`:

```typescript
import { useState } from 'react'
import { Card, Typography, Space, Input, Button, Upload, Descriptions, Tag, Alert, message } from 'antd'
import { InboxOutlined, ExperimentOutlined, UploadOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import { api } from '../../../services/api'
import { getErrorMessage } from '../../../utils'

const { Dragger } = Upload
const { Text, Title } = Typography

export interface ImportReport {
  parent_lab: string
  total_lines: number
  total_parsed: number
  inserted: number
  skipped: number
  skip_reasons: { line: number; reason: string }[]
}

interface LabImportFormProps {
  onSuccess?: (report: ImportReport) => void
}

const LabImportForm: React.FC<LabImportFormProps> = ({ onSuccess }) => {
  const [parentLab, setParentLab] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [report, setReport] = useState<ImportReport | null>(null)

  const beforeUpload: UploadProps['beforeUpload'] = (file) => {
    const isJsonl = file.name.endsWith('.jsonl') || file.type === 'application/jsonl' || file.type === ''
    if (!isJsonl) {
      message.error('请上传 .jsonl 文件')
      return Upload.LIST_IGNORE
    }
    setSelectedFile(file)
    return false
  }

  const onRemove = () => {
    setSelectedFile(null)
    setReport(null)
  }

  const handleImport = async () => {
    if (!selectedFile) {
      message.warning('请先选择 JSONL 文件')
      return
    }
    if (!parentLab.trim()) {
      message.warning('请填写实验室名称')
      return
    }
    setUploading(true)
    setReport(null)
    try {
      const res = await api.lab.importUpload(selectedFile, parentLab.trim())
      setReport(res.data as ImportReport)
      setSelectedFile(null)
      message.success(`导入完成：${res.data.inserted} 人入库，${res.data.skipped} 行跳过`)
      onSuccess?.(res.data as ImportReport)
    } catch (e) {
      message.error(getErrorMessage(e, '导入失败'))
    } finally {
      setUploading(false)
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Title level={5}>
          <ExperimentOutlined style={{ marginRight: 8 }} />
          AI 实验室人才导入
        </Title>
        <Text type="secondary">
          上传 ai-lab-talent-crawler 产出的 JSONL 文件，按实验室全量替换。
        </Text>

        <div style={{ marginTop: 16 }}>
          <Text strong>实验室名称（parent_lab）</Text>
          <Input
            placeholder="如：Stanford AI Lab"
            value={parentLab}
            onChange={(e) => setParentLab(e.target.value)}
            style={{ marginTop: 4, maxWidth: 400 }}
          />
          <Text type="secondary" style={{ display: 'block', fontSize: 12, marginTop: 4 }}>
            必填，对应 labs.yaml 里的实验室 name；本次导入会替换该实验室的全部人才数据
          </Text>
        </div>

        <div style={{ marginTop: 16 }}>
          <Dragger
            accept=".jsonl"
            maxCount={1}
            beforeUpload={beforeUpload}
            onRemove={onRemove}
            fileList={
              selectedFile
                ? [{ uid: '-1', name: selectedFile.name, status: 'done' }]
                : []
            }
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">点击或拖拽 JSONL 文件到此区域上传</p>
            <p className="ant-upload-hint">仅支持单个 .jsonl 文件（crawler 输出格式）</p>
          </Dragger>
        </div>

        <div style={{ marginTop: 16 }}>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            loading={uploading}
            onClick={handleImport}
            disabled={!selectedFile || !parentLab.trim()}
          >
            开始导入
          </Button>
        </div>
      </Card>

      {report && (
        <Card title="导入报告">
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="实验室">{report.parent_lab}</Descriptions.Item>
            <Descriptions.Item label="总行数">{report.total_lines}</Descriptions.Item>
            <Descriptions.Item label="成功解析"><Tag color="green">{report.total_parsed}</Tag></Descriptions.Item>
            <Descriptions.Item label="写入"><Tag color="blue">{report.inserted}</Tag></Descriptions.Item>
            <Descriptions.Item label="跳过"><Tag color={report.skipped > 0 ? 'warning' : 'default'}>{report.skipped}</Tag></Descriptions.Item>
          </Descriptions>

          {report.skip_reasons.length > 0 && (
            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              message={`${report.skip_reasons.length} 行被跳过（前 50 条）`}
              description={
                <div style={{ maxHeight: 200, overflow: 'auto' }}>
                  {report.skip_reasons.map((r, i) => (
                    <div key={i} style={{ fontSize: 12 }}>
                      <Text type="secondary">行 {r.line}：</Text>
                      <Text>{r.reason}</Text>
                    </div>
                  ))}
                </div>
              }
            />
          )}
        </Card>
      )}
    </Space>
  )
}

export default LabImportForm
```

- [ ] **Step 9：运行 type-check**

Run: `cd frontend && npm run type-check`

Expected: pass.

- [ ] **Step 10：Commit**

```bash
cd D:/AI/AI4TALENT
git add frontend/src/pages/lab/components/
git commit -m "feat(lab): add lab UI components (hero, charts, cards, filters, header, import)"
```

---

## Task 5：重构概览页

**Files:**
- Modify: `frontend/src/pages/lab/lab-overview-page.tsx`

- [ ] **Step 1：重写 lab-overview-page.tsx**

Replace contents of `frontend/src/pages/lab/lab-overview-page.tsx` with:

```typescript
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Row, Col, Card, Tag, Typography } from 'antd'
import { UserOutlined, ExperimentOutlined, TeamOutlined } from '@ant-design/icons'
import { useLabStats } from '../../hooks/useLabQueries'
import { applyDomainCssVars } from '../../theme'
import LabHero from './components/lab-hero'
import LabStatCard from './components/lab-stat-card'
import LabDistributionChart from './components/lab-distribution-chart'
import RoleDistributionChart from './components/role-distribution-chart'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import { useAuth } from '../../contexts/AuthContext'

const { Text } = Typography

const LabOverviewPage: React.FC = () => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { data: stats, isLoading, error, refetch } = useLabStats()

  useEffect(() => {
    applyDomainCssVars('lab')
  }, [])

  if (isLoading) return <PageSkeleton />

  if (error) {
    return (
      <EmptyPlaceholder
        title="加载失败"
        description={error.message || '请稍后重试'}
        action={{ label: '重试', onClick: () => refetch() }}
      />
    )
  }

  if (!stats || stats.total_talents === 0) {
    return (
      <EmptyPlaceholder
        title="暂无 AI 实验室人才数据"
        description="请通过 hermes 推送或管理员上传导入实验室人才数据"
        action={
          user?.role === 'super_admin'
            ? { label: '去导入', onClick: () => navigate('/system-config?tab=lab-import') }
            : undefined
        }
      />
    )
  }

  const roleData = stats.role_distribution.map((r) => ({ name: r.name, value: r.count }))
  const labData = stats.parent_lab_distribution.map((l) => ({ name: l.name, value: l.count }))

  return (
    <div>
      <LabHero />
      <div style={{ padding: 24, background: 'var(--color-bg-gray-light)', minHeight: 'calc(100vh - 300px)' }}>
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={8}>
            <LabStatCard title="人才总数" value={stats.total_talents} icon={<UserOutlined />} />
          </Col>
          <Col xs={24} sm={8}>
            <LabStatCard title="顶级实验室" value={stats.total_parent_labs} icon={<ExperimentOutlined />} />
          </Col>
          <Col xs={24} sm={8}>
            <LabStatCard title="子实验室/研究组" value={stats.total_sub_labs} icon={<TeamOutlined />} />
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card title="实验室分布" style={{ borderRadius: 12, height: '100%' }}>
              <LabDistributionChart
                data={labData}
                onBarClick={(name) => navigate(`/lab/search?parent_lab=${encodeURIComponent(name)}`)}
              />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="角色分布" style={{ borderRadius: 12, height: '100%' }}>
              <RoleDistributionChart
                data={roleData}
                onSliceClick={(name) => navigate(`/lab/search?role_type=${encodeURIComponent(name)}`)}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="学位层次" style={{ borderRadius: 12 }}>
              {stats.academic_level_distribution.map((l) => (
                <div key={l.name} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}>
                  <Text>{l.name}</Text>
                  <Tag color="blue">{l.count}</Tag>
                </div>
              ))}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="热门研究组" style={{ borderRadius: 12 }}>
              {stats.top_labs.map((lab) => (
                <Tag
                  key={lab.name}
                  style={{ marginBottom: 8, cursor: 'pointer', fontSize: 13 }}
                  onClick={() => navigate(`/lab/search?lab_name=${encodeURIComponent(lab.name)}`)}
                >
                  {lab.name} ({lab.count})
                </Tag>
              ))}
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  )
}

export default LabOverviewPage
```

- [ ] **Step 2：运行 type-check**

Run: `cd frontend && npm run type-check`

Expected: pass.

- [ ] **Step 3：Commit**

```bash
cd D:/AI/AI4TALENT
git add frontend/src/pages/lab/lab-overview-page.tsx
git commit -m "feat(lab): refactor overview page with hero, charts and React Query"
```

---

## Task 6：重构搜索页

**Files:**
- Modify: `frontend/src/pages/lab/lab-search-page.tsx`

- [ ] **Step 1：重写 lab-search-page.tsx**

Replace contents of `frontend/src/pages/lab/lab-search-page.tsx` with:

```typescript
import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Row, Col, Card, Pagination, Space, Typography, Spin } from 'antd'
import { useLabTalents } from '../../hooks/useLabQueries'
import { useLabSearchStore } from '../../stores/labSearchStore'
import { applyDomainCssVars } from '../../theme'
import LabSearchFilter from './components/lab-search-filter'
import LabTalentCard from './components/lab-talent-card'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import BreadcrumbNav from '../../components/BreadcrumbNav'

const { Text } = Typography

const LabSearchPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const state = useLabSearchStore()

  useEffect(() => {
    applyDomainCssVars('lab')
  }, [])

  useEffect(() => {
    state.syncFromUrl(searchParams)
  }, [])

  useEffect(() => {
    const query = state.toQuery()
    setSearchParams(query, { replace: true })
  }, [
    state.keyword,
    state.parentLab,
    state.labName,
    state.roleType,
    state.academicLevel,
    state.researchArea,
    state.sortBy,
    state.page,
    state.pageSize,
    state.advancedOpen,
    setSearchParams,
  ])

  const { data, isLoading, error, refetch } = useLabTalents({
    keyword: state.keyword || undefined,
    parent_lab: state.parentLab || undefined,
    lab_name: state.labName || undefined,
    role_type: state.roleType || undefined,
    academic_level: state.academicLevel || undefined,
    research_area: state.researchArea || undefined,
    sort_by: state.sortBy === 'default' ? undefined : state.sortBy,
    page: state.page,
    page_size: state.pageSize,
  })

  if (error) {
    return (
      <EmptyPlaceholder
        title="加载失败"
        description={error.message || '请稍后重试'}
        action={{ label: '重试', onClick: () => refetch() }}
      />
    )
  }

  const items = data?.data || []
  const total = data?.total || 0

  return (
    <div style={{ padding: 24, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      <BreadcrumbNav items={[{ label: '实验室', path: '/lab' }, { label: '搜索' }]} />
      <LabSearchFilter state={state} />

      <Spin spinning={isLoading}>
        <Card style={{ borderRadius: 12 }}>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary">共 {total} 人</Text>
          </div>

          {items.length === 0 && !isLoading ? (
            <EmptyPlaceholder
              title="未找到匹配的人才"
              description="尝试调整筛选条件"
              action={{ label: '清除筛选', onClick: () => state.resetFilters() }}
            />
          ) : (
            <>
              <Row gutter={[16, 16]}>
                {items.map((t) => (
                  <Col xs={24} sm={12} md={8} lg={6} key={t.talent_id}>
                    <LabTalentCard talent={t} />
                  </Col>
                ))}
              </Row>
              <div style={{ textAlign: 'center', marginTop: 24 }}>
                <Pagination
                  current={state.page}
                  total={total}
                  pageSize={state.pageSize}
                  onChange={(p) => state.setFilter('page', p)}
                  showTotal={(t) => `共 ${t} 人`}
                />
              </div>
            </>
          )}
        </Card>
      </Spin>
    </div>
  )
}

export default LabSearchPage
```

- [ ] **Step 2：运行 type-check**

Run: `cd frontend && npm run type-check`

Expected: pass.

- [ ] **Step 3：Commit**

```bash
cd D:/AI/AI4TALENT
git add frontend/src/pages/lab/lab-search-page.tsx
git commit -m "feat(lab): refactor search page with Zustand, URL sync and React Query"
```

---

## Task 7：重构详情页

**Files:**
- Modify: `frontend/src/pages/lab/lab-talent-detail-page.tsx`

- [ ] **Step 1：重写 lab-talent-detail-page.tsx**

Replace contents of `frontend/src/pages/lab/lab-talent-detail-page.tsx` with:

```typescript
import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Row, Col, Card, Descriptions, Tag, Typography, Button, Space, Divider } from 'antd'
import { ArrowLeftOutlined, HomeOutlined, MailOutlined } from '@ant-design/icons'
import { useLabTalent } from '../../hooks/useLabQueries'
import { applyDomainCssVars } from '../../theme'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import BreadcrumbNav from '../../components/BreadcrumbNav'
import LabTalentHeader from './components/lab-talent-header'

const { Title, Text, Link } = Typography

const LabTalentDetailPage: React.FC = () => {
  const { talentId } = useParams<{ talentId: string }>()
  const navigate = useNavigate()
  const id = talentId ? Number(talentId) : undefined
  const { data: talent, isLoading, error } = useLabTalent(id)

  useEffect(() => {
    applyDomainCssVars('lab')
  }, [])

  if (isLoading) return <PageSkeleton />

  if (error || !talent) {
    return (
      <EmptyPlaceholder
        title="人才不存在或已删除"
        description="该人才可能已被移除或链接有误"
        action={{ label: '返回搜索页', onClick: () => navigate('/lab/search') }}
      />
    )
  }

  return (
    <div style={{ padding: 24, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      <BreadcrumbNav
        items={[
          { label: '实验室', path: '/lab' },
          { label: '搜索', path: '/lab/search' },
          { label: talent.name },
        ]}
      />

      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
        返回
      </Button>

      <Row gutter={[24, 24]}>
        <Col xs={24} md={8} lg={7} xl={6}>
          <Card style={{ borderRadius: 12, position: 'sticky', top: 24 }}>
            <LabTalentHeader talent={talent} />
          </Card>
        </Col>
        <Col xs={24} md={16} lg={17} xl={18}>
          <Card style={{ borderRadius: 12 }}>
            <Title level={4} style={{ marginTop: 0 }}>基本信息</Title>
            <Descriptions column={1} bordered size="small" labelStyle={{ width: 140 }}>
              <Descriptions.Item label="顶级实验室">{talent.parent_lab}</Descriptions.Item>
              {talent.lab_name && talent.lab_name !== talent.parent_lab && (
                <Descriptions.Item label="研究组">{talent.lab_name}</Descriptions.Item>
              )}
              {talent.department && <Descriptions.Item label="院系">{talent.department}</Descriptions.Item>}
              {talent.cohort_year && (
                <Descriptions.Item label="入学/加入年份">{talent.cohort_year}</Descriptions.Item>
              )}
              {talent.cohort_source && (
                <Descriptions.Item label="届别来源">{talent.cohort_source}</Descriptions.Item>
              )}
              {talent.email && (
                <Descriptions.Item label="邮箱">
                  <Space>
                    <MailOutlined />
                    <Link href={`mailto:${talent.email}`}>{talent.email}</Link>
                  </Space>
                </Descriptions.Item>
              )}
              {talent.homepage && (
                <Descriptions.Item label="个人主页">
                  <Space>
                    <HomeOutlined />
                    <Link href={talent.homepage} target="_blank">{talent.homepage}</Link>
                  </Space>
                </Descriptions.Item>
              )}
            </Descriptions>

            {talent.research_areas && talent.research_areas.length > 0 && (
              <>
                <Divider />
                <Title level={4}>研究方向</Title>
                <Space size={8} wrap>
                  {talent.research_areas.map((a) => (
                    <Tag key={a} color="geekblue">{a}</Tag>
                  ))}
                </Space>
              </>
            )}

            <Divider />
            <Text type="secondary" style={{ fontSize: 12 }}>
              数据来源：{talent.parent_lab} 官网
              {talent.collected_at && ` · 采集于 ${talent.collected_at.slice(0, 10)}`}
            </Text>
            {talent.source_detail_url && (
              <div>
                <Link href={talent.source_detail_url} target="_blank" style={{ fontSize: 12 }}>
                  查看来源页面
                </Link>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default LabTalentDetailPage
```

- [ ] **Step 2：运行 type-check**

Run: `cd frontend && npm run type-check`

Expected: pass.

- [ ] **Step 3：Commit**

```bash
cd D:/AI/AI4TALENT
git add frontend/src/pages/lab/lab-talent-detail-page.tsx
git commit -m "feat(lab): refactor detail page with two-column layout and React Query"
```

---

## Task 8：重构导入 Tab

**Files:**
- Modify: `frontend/src/pages/system-config/components/lab-import-tab.tsx`

- [ ] **Step 1：简化 lab-import-tab.tsx 使用 LabImportForm**

Replace contents of `frontend/src/pages/system-config/components/lab-import-tab.tsx` with:

```typescript
import LabImportForm from '../../lab/components/lab-import-form'

const LabImportTab: React.FC = () => {
  return <LabImportForm />
}

export default LabImportTab
```

- [ ] **Step 2：运行 type-check**

Run: `cd frontend && npm run type-check`

Expected: pass.

- [ ] **Step 3：Commit**

```bash
cd D:/AI/AI4TALENT
git add frontend/src/pages/system-config/components/lab-import-tab.tsx
git commit -m "refactor(lab-import): use extracted LabImportForm component"
```

---

## Task 9：组件单元测试

**Files:**
- Create: `frontend/src/pages/lab/components/__tests__/lab-stat-card.test.tsx`
- Create: `frontend/src/pages/lab/components/__tests__/lab-search-filter.test.tsx`
- Create: `frontend/src/pages/lab/components/__tests__/lab-talent-card.test.tsx`
- Create: `frontend/src/pages/lab/components/__tests__/lab-talent-header.test.tsx`

- [ ] **Step 1：创建 lab-stat-card.test.tsx**

Create `frontend/src/pages/lab/components/__tests__/lab-stat-card.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { UserOutlined } from '@ant-design/icons'
import LabStatCard from '../lab-stat-card'

describe('LabStatCard', () => {
  it('renders title and value', () => {
    render(<LabStatCard title="人才总数" value={108} icon={<UserOutlined data-testid="user-icon" />} />)
    expect(screen.getByText('人才总数')).toBeInTheDocument()
    expect(screen.getByText('108')).toBeInTheDocument()
    expect(screen.getByTestId('user-icon')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2：创建 lab-search-filter.test.tsx**

Create `frontend/src/pages/lab/components/__tests__/lab-search-filter.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import LabSearchFilter from '../lab-search-filter'

describe('LabSearchFilter', () => {
  const mockState = {
    keyword: '',
    parentLab: '',
    labName: '',
    roleType: '',
    academicLevel: '',
    researchArea: '',
    sortBy: 'default' as const,
    page: 1,
    pageSize: 20,
    advancedOpen: false,
    setFilter: vi.fn(),
    resetFilters: vi.fn(),
    toggleAdvanced: vi.fn(),
    syncFromUrl: vi.fn(),
    toQuery: vi.fn(() => ({})),
  }

  it('renders core filters', () => {
    render(<LabSearchFilter state={mockState} />)
    expect(screen.getByPlaceholderText('输入姓名关键词...')).toBeInTheDocument()
    expect(screen.getByText('高级筛选')).toBeInTheDocument()
    expect(screen.getByText('重置')).toBeInTheDocument()
  })

  it('calls resetFilters when reset clicked', () => {
    render(<LabSearchFilter state={mockState} />)
    fireEvent.click(screen.getByText('重置'))
    expect(mockState.resetFilters).toHaveBeenCalled()
  })

  it('toggles advanced filters', () => {
    render(<LabSearchFilter state={mockState} />)
    fireEvent.click(screen.getByText('高级筛选'))
    expect(mockState.toggleAdvanced).toHaveBeenCalled()
  })
})
```

- [ ] **Step 3：创建 lab-talent-card.test.tsx**

Create `frontend/src/pages/lab/components/__tests__/lab-talent-card.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import LabTalentCard from '../lab-talent-card'
import type { LabTalent } from '../../../../types'

const mockTalent: LabTalent = {
  talent_id: 1,
  name: '周志华',
  role_section: 'faculty',
  role_type: 'professor',
  academic_level: 'phd',
  current_title: '教授',
  homepage: null,
  department: null,
  research_areas: ['machine learning', 'data mining'],
  cohort_year: null,
  lab_name: 'LAMDA',
  parent_lab: '南京大学LAMDA实验室',
}

describe('LabTalentCard', () => {
  it('renders name, role and research areas', () => {
    render(<LabTalentCard talent={mockTalent} />)
    expect(screen.getByText('周志华')).toBeInTheDocument()
    expect(screen.getByText('教授')).toBeInTheDocument()
    expect(screen.getByText('博士')).toBeInTheDocument()
    expect(screen.getByText('machine learning')).toBeInTheDocument()
  })

  it('truncates research areas with +N', () => {
    const manyAreas = { ...mockTalent, research_areas: ['a', 'b', 'c', 'd', 'e'] }
    render(<LabTalentCard talent={manyAreas} />)
    expect(screen.getByText('+1')).toBeInTheDocument()
  })
})
```

- [ ] **Step 4：创建 lab-talent-header.test.tsx**

Create `frontend/src/pages/lab/components/__tests__/lab-talent-header.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import LabTalentHeader from '../lab-talent-header'
import type { LabTalentDetail } from '../../../../types'

const mockTalent: LabTalentDetail = {
  talent_id: 1,
  name: '周志华',
  role_section: 'faculty',
  role_type: 'professor',
  academic_level: 'phd',
  current_title: '教授',
  homepage: 'http://cs.nju.edu.cn/zhouzh',
  department: '计算机系',
  research_areas: ['machine learning'],
  cohort_year: null,
  lab_name: 'LAMDA',
  parent_lab: '南京大学LAMDA实验室',
  email: 'zhouzh@nju.edu.cn',
  photo_url: null,
  cohort_source: null,
  source_url: null,
  source_detail_url: null,
  collected_at: null,
}

describe('LabTalentHeader', () => {
  it('renders name, role and contact buttons', () => {
    render(<LabTalentHeader talent={mockTalent} />)
    expect(screen.getByText('周志华')).toBeInTheDocument()
    expect(screen.getByText('教授')).toBeInTheDocument()
    expect(screen.getByText('zhouzh@nju.edu.cn')).toBeInTheDocument()
    expect(screen.getByText('个人主页')).toBeInTheDocument()
  })
})
```

- [ ] **Step 5：运行组件测试**

Run: `cd frontend && npx vitest run src/pages/lab/components/__tests__`

Expected: all tests pass.

- [ ] **Step 6：Commit**

```bash
cd D:/AI/AI4TALENT
git add frontend/src/pages/lab/components/__tests__
git commit -m "test(lab): add unit tests for lab components"
```

---

## Task 10：代码检查与类型检查

**Files:** all modified files.

- [ ] **Step 1：运行 Prettier 格式检查**

Run: `cd frontend && npm run format:check`

Expected: no unformatted files. If fails, run `npm run format` and re-run.

- [ ] **Step 2：运行 ESLint**

Run: `cd frontend && npm run lint`

Expected: no lint errors.

- [ ] **Step 3：运行 TypeScript 类型检查**

Run: `cd frontend && npm run type-check`

Expected: pass.

- [ ] **Step 4：运行所有单元测试**

Run: `cd frontend && npm run test`

Expected: all tests pass.

- [ ] **Step 5：Commit fixes**

```bash
cd D:/AI/AI4TALENT
git add -A
git commit -m "chore(lab): fix lint, format and type errors"
```

---

## Task 11：浏览器手动验证

**Files:** n/a (manual QA)

- [ ] **Step 1：启动前端开发服务器**

Run: `cd frontend && npm run dev`

Expected: dev server starts on http://localhost:2012

- [ ] **Step 2：登录并访问概览页**

Navigate to `http://localhost:2012/lab`.

Verify:
- Hero 区深蓝渐变背景显示
- 3 个统计卡片显示正确数字
- 实验室分布条形图显示
- 角色分布环形图显示
- 点击图表元素跳转搜索页并携带参数

- [ ] **Step 3：验证搜索页**

Verify:
- 核心筛选（姓名、角色、学位、排序、重置）工作正常
- 高级筛选展开/折叠正常
- 修改筛选自动重置到第 1 页
- URL 同步筛选条件和页码
- 人才卡片显示头像占位、姓名、角色、学位、实验室、研究方向
- `&nbsp` 等 HTML 实体已解码

- [ ] **Step 4：验证详情页**

Verify:
- 左右分栏布局
- 头像占位显示姓名首字母
- 角色/学位标签显示
- 联系方式按钮可点击
- 返回按钮回到上一页
- 不存在的 talentId 显示 404 空状态

- [ ] **Step 5：验证导入页**

Navigate to `http://localhost:2012/system-config?tab=lab-import`.

Verify:
- 导入表单主题色统一
- 未选择文件或实验室时按钮禁用
- 导入成功后文件列表清空

- [ ] **Step 6：提交验证截图（可选）**

Take screenshots of `/lab`, `/lab/search`, `/lab/talents/1` and save to `outputs/screenshots/lab-*.png`.

- [ ] **Step 7：Commit verification notes**

```bash
cd D:/AI/AI4TALENT
git add outputs/screenshots/lab-*.png
git commit -m "docs(lab): add verification screenshots"
```

---

## Self-Review Checklist

### 1. Spec coverage

| Spec 需求 | 对应 Task |
|---|---|
| 概览页 Hero + 统计卡片 + 图表 | Task 4 (components), Task 5 |
| 搜索页筛选/排序/重置/URL 同步 | Task 2 (store), Task 4 (filter), Task 6 |
| 人才卡片头像占位 + HTML 实体解码 | Task 4 (card), Task 9 |
| 详情页左右分栏 + 联系方式 | Task 4 (header), Task 7 |
| 导入页主题色 + 成功后清空 | Task 4 (form), Task 8 |
| React Query + Zustand | Task 1, Task 2 |
| 骨架屏 + 空状态 + 面包屑 | Task 3, Task 5/6/7 |
| 单元测试 | Task 9 |

### 2. Placeholder scan

- No TBD/TODO/fill-in-later patterns found.
- All steps include concrete file paths, code, and commands.

### 3. Type consistency

- `LabSearchState` interface used consistently across store and filter component.
- `LabTalent`, `LabTalentDetail`, `LabStats` types reused from existing `types/index.ts`.
- Query keys follow existing `queryKeys` pattern.

### 4. Known gaps / decisions

- `research_area` 在 API 中以单字符串实现（设计文档中为多选）。本次实现先用单 Input，后端支持多选后再升级。
- `decodeHtmlEntities` 使用 DOM textarea，运行在浏览器环境；Vitest jsdom 支持此 API。
- `useAuth` context 用于判断管理员，沿用项目现有模式。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-04-lab-ux-optimization-plan.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Which approach?
