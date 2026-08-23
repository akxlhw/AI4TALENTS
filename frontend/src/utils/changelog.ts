/** Keep-a-Changelog 子集解析器。
 *
 * CHANGELOG.md 经 vite `?raw` 在构建期打包（路径仅在此处出现一次）；
 * 运行时解析为结构化版本数组供更新日志抽屉渲染。任何段落解析失败只
 * 跳过该段，绝不抛错。 */

import changelogRaw from '../../../CHANGELOG.md?raw'

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

/** 条目按纯文本展示：剥离 CHANGELOG 里的加粗/行内代码记号 */
const stripMarkdown = (s: string): string => s.replace(/\*\*/g, '').replace(/`/g, '').trim()

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
        text: stripMarkdown(itemMatch[2]),
      })
      continue
    }

    const introMatch = line.match(/^> ?(.*)$/)
    if (introMatch && current.sections.length === 0) {
      const text = stripMarkdown(introMatch[1])
      if (text) introLines.push(text)
    }
  }

  // 只有引言没有分组的版本（当前不存在，但保持健壮）
  if (
    current &&
    current.sections.length === 0 &&
    current.intro === null &&
    introLines.length > 0
  ) {
    current.intro = introLines.join(' ')
  }
  return releases
}

/** 构建期打包的真实 CHANGELOG 预解析结果（模块级缓存）。
 * 解析异常降级为空数组 → 抽屉显示空态。 */
export const CHANGELOG_RELEASES: ChangelogRelease[] = (() => {
  try {
    return parseChangelog(changelogRaw)
  } catch {
    return []
  }
})()
