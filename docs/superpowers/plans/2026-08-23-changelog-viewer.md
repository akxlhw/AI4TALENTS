# 系统更新日志查看（Changelog Viewer）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 所有登录用户可在导航栏打开「更新日志」抽屉，按版本时间线查看 CHANGELOG.md 的迭代记录，新版本未读时入口带红点。

**Architecture:** CHANGELOG.md 在前端构建期经 vite `?raw` 打包进产物；`parseChangelog()` 纯函数按 Keep a Changelog 子集解析为结构化版本数组；`ChangelogDrawer` 用 antd Drawer + Collapse 渲染；MainLayout 持有抽屉开合状态与 localStorage 已读标记。零后端改动、零新依赖。

**Tech Stack:** React 18 + TypeScript + antd v5（Drawer/Collapse/Badge/Tag/Timeline 不新增依赖）+ Vitest + @testing-library/react

**设计文档:** `docs/superpowers/specs/2026-08-23-changelog-viewer-design.md`

---

### Task 1: CHANGELOG 解析器（TDD）

**Files:**
- Create: `frontend/src/utils/changelog.ts`
- Test: `frontend/src/utils/changelog.test.ts`

- [ ] **Step 1: 写失败测试**

创建 `frontend/src/utils/changelog.test.ts`：

```ts
import { describe, expect, it } from 'vitest'

import { parseChangelog } from './changelog'

const SAMPLE = `# Changelog

All notable changes.

## [Unreleased]

## [5.0.1] - 2026-08-22

### Fixed

- 修复分页双触发竞态
  - 含子条目说明

## [5.0.0] - 2026-08-16

> 主交付：行业人才库 + 技术分类体系 v2。

### Added

- **行业人才库**（domains/industry/）：三表模型、增量导入
- **技术分类体系 v2**：三层分类

### Changed

- 依赖安全升级

## [3.0.0]
`

describe('parseChangelog', () => {
  it('parses releases newest-first with sections and nested items', () => {
    const releases = parseChangelog(SAMPLE)
    expect(releases).toHaveLength(3)

    const [latest, major, noDate] = releases
    expect(latest.version).toBe('5.0.1')
    expect(latest.date).toBe('2026-08-22')
    expect(latest.intro).toBeNull()
    expect(latest.sections).toEqual([
      { group: 'Fixed', items: [{ level: 1, text: '修复分页双触发竞态' }, { level: 2, text: '含子条目说明' }] },
    ])

    expect(major.version).toBe('5.0.0')
    expect(major.intro).toContain('行业人才库')
    expect(major.sections.map(s => s.group)).toEqual(['Added', 'Changed'])
    expect(major.sections[0].items).toHaveLength(2)

    expect(noDate.version).toBe('3.0.0')
    expect(noDate.date).toBeNull()
    expect(noDate.sections).toEqual([])
  })

  it('skips the Unreleased section', () => {
    const releases = parseChangelog(SAMPLE)
    expect(releases.some(r => r.version === 'Unreleased')).toBe(false)
  })

  it('returns empty array for malformed input without throwing', () => {
    expect(parseChangelog('')).toEqual([])
    expect(parseChangelog('not a changelog at all')).toEqual([])
  })
})
```

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npx vitest run src/utils/changelog.test.ts`
Expected: FAIL — 无法解析 `./changelog`（模块不存在）

- [ ] **Step 3: 实现解析器**

创建 `frontend/src/utils/changelog.ts`：

```ts
/** Keep-a-Changelog 子集解析器。
 *
 * CHANGELOG.md 经 vite `?raw` 在构建期打包；本模块在运行时解析为结构化
 * 版本数组供更新日志抽屉渲染。任何段落解析失败只跳过该段，绝不抛错。 */

export interface ChangelogItem {
  level: 1 | 2
  text: string
}

export interface ChangelogSection {
  group: string
  items: ChangelogItem[]
}

export interface ChangelogRelease {
  version: string
  date: string | null
  /** 版本标题下、首个分组前的引言（blockquote） */
  intro: string | null
  sections: ChangelogSection[]
}

const RELEASE_RE = /^## \[([^\]]+)\](?:\s+-\s+(.+))?$/
const SECTION_RE = /^### (.+)$/
const ITEM_RE = /^(\s*)- (.+)$/

export function parseChangelog(raw: string): ChangelogRelease[] {
  const releases: ChangelogRelease[] = []
  let current: ChangelogRelease | null = null
  let currentSection: ChangelogSection | null = null
  let introLines: string[] = []

  for (const line of raw.split(/\r?\n/)) {
    const releaseMatch = line.match(RELEASE_RE)
    if (releaseMatch) {
      current = null
      currentSection = null
      introLines = []
      if (releaseMatch[1] === 'Unreleased') continue
      current = {
        version: releaseMatch[1],
        date: releaseMatch[2] ?? null,
        intro: null,
        sections: [],
      }
      releases.push(current)
      continue
    }
    if (!current) continue

    const sectionMatch = line.match(SECTION_RE)
    if (sectionMatch) {
      if (introLines.length > 0 && current.sections.length === 0) {
        current.intro = introLines.join(' ')
      }
      introLines = []
      currentSection = { group: sectionMatch[1].trim(), items: [] }
      current.sections.push(currentSection)
      continue
    }

    const itemMatch = line.match(ITEM_RE)
    if (itemMatch) {
      if (!currentSection) continue
      currentSection.items.push({
        level: itemMatch[1].length >= 2 ? 2 : 1,
        text: itemMatch[2].trim(),
      })
      continue
    }

    const introMatch = line.match(/^> ?(.*)$/)
    if (introMatch && current.sections.length === 0) {
      const text = introMatch[1].trim()
      if (text) introLines.push(text)
    }
  }

  // 只有引言没有分组的版本（当前不存在，但保持健壮）
  if (current && current.sections.length === 0 && current.intro === null && introLines.length > 0) {
    current.intro = introLines.join(' ')
  }
  return releases
}
```

- [ ] **Step 4: 运行确认通过**

Run: `cd frontend && npx vitest run src/utils/changelog.test.ts`
Expected: PASS（3 个用例）

- [ ] **Step 5: 用真实 CHANGELOG 冒烟**

在测试文件末尾追加（验证真实文件格式可解析、最新版本非空）：

```ts
import realChangelog from '../../../CHANGELOG.md?raw'

describe('parseChangelog with the real CHANGELOG.md', () => {
  it('parses the bundled real changelog', () => {
    const releases = parseChangelog(realChangelog)
    expect(releases.length).toBeGreaterThan(3)
    expect(releases[0].version).toMatch(/^\d+\.\d+\.\d+$/)
    expect(releases[0].sections.length).toBeGreaterThan(0)
  })
})
```

Run: `cd frontend && npx vitest run src/utils/changelog.test.ts`
Expected: PASS（4 个用例）

- [ ] **Step 6: 提交**

```bash
git add frontend/src/utils/changelog.ts frontend/src/utils/changelog.test.ts
git commit -m "feat: CHANGELOG.md 解析器（Keep a Changelog 子集，容错跳过异常段）"
```

---

### Task 2: 更新日志抽屉组件

**Files:**
- Create: `frontend/src/components/ChangelogDrawer.tsx`
- Test: `frontend/src/components/ChangelogDrawer.test.tsx`

- [ ] **Step 1: 写失败测试**

创建 `frontend/src/components/ChangelogDrawer.test.tsx`：

```tsx
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

import ChangelogDrawer from './ChangelogDrawer'

describe('ChangelogDrawer', () => {
  it('renders the latest version badge, group tags and item text when open', () => {
    render(<ChangelogDrawer open onClose={vi.fn()} />)
    expect(screen.getAllByText('最新').length).toBeGreaterThan(0)
    expect(screen.getByText('Added')).toBeTruthy()
    expect(screen.getByText('Changed')).toBeTruthy()
    expect(screen.getByText('Fixed')).toBeTruthy()
  })

  it('shows an empty state when nothing parsed', () => {
    render(<ChangelogDrawer open onClose={vi.fn()} forceEmpty />)
    expect(screen.getByText('暂无更新记录')).toBeTruthy()
  })

  it('calls onClose when the drawer close button is clicked', () => {
    const onClose = vi.fn()
    render(<ChangelogDrawer open onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npx vitest run src/components/ChangelogDrawer.test.tsx`
Expected: FAIL — 模块不存在

- [ ] **Step 3: 实现抽屉组件**

创建 `frontend/src/components/ChangelogDrawer.tsx`：

```tsx
import { Alert, Collapse, Drawer, Empty, Space, Tag, Typography } from 'antd'
import changelogRaw from '../../CHANGELOG.md?raw'
import { parseChangelog, type ChangelogRelease } from '../utils/changelog'

const { Text, Title } = Typography

const GROUP_COLORS: Record<string, string> = {
  Added: 'green',
  Changed: 'blue',
  Fixed: 'orange',
  Removed: 'red',
  Security: 'purple',
}

/** 解析一次（模块级缓存）；解析失败降级为空数组 → 抽屉空态 */
const releases: ChangelogRelease[] = (() => {
  try {
    return parseChangelog(changelogRaw)
  } catch {
    return []
  }
})()

const ChangelogDrawer: React.FC<{
  open: boolean
  onClose: () => void
  /** 仅供测试：强制渲染空态 */
  forceEmpty?: boolean
}> = ({ open, onClose, forceEmpty = false }) => {
  const list = forceEmpty ? [] : releases
  const latestVersion = releases[0]?.version

  return (
    <Drawer
      title={
        <Space direction="vertical" size={0}>
          <Title level={5} style={{ margin: 0 }}>
            更新日志
          </Title>
          {latestVersion && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              当前版本 v{latestVersion}
            </Text>
          )}
        </Space>
      }
      placement="right"
      width={520}
      open={open}
      onClose={onClose}
    >
      {list.length === 0 ? (
        <Empty description="暂无更新记录" style={{ marginTop: 80 }} />
      ) : (
        <>
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
            message="版本由新到旧排列，展开任意版本查看完整变更明细。"
          />
          <Collapse
            defaultActiveKey={[list[0].version]}
            items={list.map(r => ({
              key: r.version,
              label: (
                <Space size={8}>
                  <Text strong>v{r.version}</Text>
                  {r === list[0] && <Tag color="geekblue" style={{ margin: 0 }}>最新</Tag>}
                  {r.date && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {r.date}
                    </Text>
                  )}
                </Space>
              ),
              children: (
                <div>
                  {r.intro && (
                    <Text
                      type="secondary"
                      style={{ display: 'block', marginBottom: 8, fontSize: 12 }}
                    >
                      {r.intro}
                    </Text>
                  )}
                  {r.sections.map(section => (
                    <div key={section.group} style={{ marginBottom: 12 }}>
                      <Tag color={GROUP_COLORS[section.group] ?? 'default'} style={{ marginBottom: 4 }}>
                        {section.group}
                      </Tag>
                      {section.items.map((item, i) => (
                        <Text
                          key={i}
                          style={{
                            display: 'block',
                            fontSize: 13,
                            lineHeight: '22px',
                            paddingLeft: item.level === 2 ? 20 : 0,
                            color: item.level === 2 ? 'var(--text-secondary)' : undefined,
                          }}
                        >
                          {item.text}
                        </Text>
                      ))}
                    </div>
                  ))}
                </div>
              ),
            }))}
          />
        </>
      )}
    </Drawer>
  )
}

export default ChangelogDrawer
```

注意：`../../CHANGELOG.md?raw` 的相对路径——组件位于 `frontend/src/components/`，`../../` 即仓库根。若 lint 报 import 顺序，把静态导入移到文件顶部 import 区。

- [ ] **Step 4: 运行确认通过**

Run: `cd frontend && npx vitest run src/components/ChangelogDrawer.test.tsx`
Expected: PASS（3 个用例；真实 CHANGELOG 含 Added/Changed/Fixed 分组）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/ChangelogDrawer.tsx frontend/src/components/ChangelogDrawer.test.tsx
git commit -m "feat: 更新日志抽屉组件（版本时间线 + 分组标签 + 空态降级）"
```

---

### Task 3: MainLayout 接线（入口按钮 + 红点 + 窄屏菜单）

**Files:**
- Modify: `frontend/src/layouts/MainLayout.tsx`

- [ ] **Step 1: 加状态与导入**

在 `MainLayout.tsx` 顶部 import 区加入：

```tsx
import { Badge } from 'antd'   // 并入第 3 行 antd 导入
import { HistoryOutlined } from '@ant-design/icons'   // 并入图标导入
import ChangelogDrawer from '../components/ChangelogDrawer'
import { parseChangelog } from '../utils/changelog'
import changelogRaw from '../../CHANGELOG.md?raw'
```

组件内部（`useCollectTaskNotifier()` 调用之后）加入：

```tsx
  // 更新日志：入口红点 + 抽屉开合
  const [changelogOpen, setChangelogOpen] = useState(false)
  const latestVersion = (() => {
    try {
      return parseChangelog(changelogRaw)[0]?.version
    } catch {
      return undefined
    }
  })()
  const [changelogSeen, setChangelogSeen] = useState<string | null>(null)
  useEffect(() => {
    setChangelogSeen(localStorage.getItem('changelog_last_seen_version'))
  }, [])
  const openChangelog = () => {
    setChangelogOpen(true)
    if (latestVersion) {
      localStorage.setItem('changelog_last_seen_version', latestVersion)
      setChangelogSeen(latestVersion)
    }
  }
  const hasUnseenRelease = latestVersion !== undefined && changelogSeen !== latestVersion
```

- [ ] **Step 2: 宽屏导航按钮**

在「意见反馈」Button（`onClick={() => navigate('/feedback')}`）之后插入：

```tsx
                <Badge dot={hasUnseenRelease} offset={[-2, 2]}>
                  <Button
                    type="text"
                    size="small"
                    icon={<HistoryOutlined />}
                    onClick={openChangelog}
                    style={{ fontSize: 13 }}
                  >
                    更新日志
                  </Button>
                </Badge>
```

- [ ] **Step 3: 窄屏用户菜单项**

`isNarrow` 分支的菜单数组里 `feedback` 项后加：

```tsx
      { key: 'changelog', icon: <HistoryOutlined />, label: '更新日志' },
```

`handleUserMenuClick` 加分支（放在 feedback 分支后）：

```tsx
    else if (key === 'changelog') openChangelog()
```

- [ ] **Step 4: 挂载抽屉**

在 `<Footer />` 之前插入：

```tsx
      <ChangelogDrawer open={changelogOpen} onClose={() => setChangelogOpen(false)} />
```

- [ ] **Step 5: 验证**

Run: `cd frontend && npx tsc -b && npx eslint src/layouts/MainLayout.tsx && npm run build 2>&1 | tail -3`
Expected: 全部通过，`✓ built in`

- [ ] **Step 6: 手工验收（浏览器）**

打开 http://localhost:2012 登录 admin/admin123：
1. 导航栏出现「更新日志」按钮且带红点（首次未读）
2. 点击打开抽屉：最新版 v5.0.1（或当前最新）展开、含 Added/Changed/Fixed 分组
3. 关闭再打开：红点消失
4. 缩窄窗口到 <768px：入口收进用户菜单且可打开

- [ ] **Step 7: 提交**

```bash
git add frontend/src/layouts/MainLayout.tsx
git commit -m "feat: 导航栏更新日志入口（红点提醒 + 窄屏菜单收拢）"
```

---

### Task 4: 全量回归与推送

- [ ] **Step 1: 前端全量验证**

Run: `cd frontend && npx tsc -b && npm run test && npm run build`
Expected: tsc 零错误；全部单测通过（既有 40+ 新增 7）；构建成功

- [ ] **Step 2: 推送**

```bash
git push origin main
```

---

## Self-Review 结论

- **Spec 覆盖**：数据源（Task 1）、入口+红点+窄屏（Task 3）、抽屉时间线与空态（Task 2）、解析容错与测试（Task 1/2）、构建验证（Task 4）——设计文档各节均有对应任务
- **占位符**：无 TBD/TODO，所有代码步骤含完整代码
- **类型一致性**：`parseChangelog` / `ChangelogRelease` / `ChangelogSection` / `ChangelogItem` 在 Task 1 定义，Task 2/3 引用一致；`forceEmpty` 仅测试用 prop，已在组件签名声明
