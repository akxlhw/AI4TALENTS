import { describe, expect, it } from 'vitest'

import { CHANGELOG_RELEASES, parseChangelog } from './changelog'

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
      {
        group: 'Fixed',
        items: [
          { level: 1, text: '修复分页双触发竞态' },
          { level: 2, text: '含子条目说明' },
        ],
      },
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

describe('bundled CHANGELOG.md', () => {
  it('parses the real changelog shipped at build time', () => {
    expect(CHANGELOG_RELEASES.length).toBeGreaterThan(3)
    expect(CHANGELOG_RELEASES[0].version).toMatch(/^\d+\.\d+\.\d+$/)
    expect(CHANGELOG_RELEASES[0].sections.length).toBeGreaterThan(0)
    expect(CHANGELOG_RELEASES.some(r => r.version === 'Unreleased')).toBe(false)
  })
})
