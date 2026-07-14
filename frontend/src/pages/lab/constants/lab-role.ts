/**
 * Shared role configuration for the AI Native lab domain.
 *
 * Single source of truth for role labels, colors, and academic level labels.
 * All lab components should import from here instead of defining their own.
 */

export interface RoleConfig {
  key: string
  label: string
  /** Primary color for tags, dots, bars (hex — ECharts canvas can't use CSS vars) */
  color: string
}

/** Role display config — ordered by visual priority. */
export const ROLE_CONFIG: RoleConfig[] = [
  { key: 'professor', label: '教授', color: '#0D2B4E' },
  { key: 'student', label: '在读学生', color: '#0EA5E9' },
  { key: 'graduate', label: '博后/研究员', color: '#F59E0B' },
  { key: 'alumni', label: '已毕业', color: '#0284C7' },
  { key: 'unknown', label: '其他', color: '#CBD5E1' },
]

/** Quick lookup maps derived from ROLE_CONFIG */
export const ROLE_LABELS: Record<string, string> = Object.fromEntries(
  ROLE_CONFIG.map(r => [r.key, r.label])
)

export const ROLE_COLORS: Record<string, string> = Object.fromEntries(
  ROLE_CONFIG.map(r => [r.key, r.color])
)

/** Academic level labels */
export const LEVEL_LABELS: Record<string, string> = {
  phd: '博士',
  master: '硕士',
  bachelor: '学士',
}

/** Role filter options for search (includes "全部角色") */
export const ROLE_FILTER_OPTIONS = [
  { label: '全部角色', value: '' },
  ...ROLE_CONFIG.filter(r => r.key !== 'unknown').map(r => ({
    label: r.label,
    value: r.key,
  })),
]

/** Role tab config for lab detail page (includes "全部") */
export const ROLE_TAB_CONFIG: { key: string; label: string }[] = [
  { key: '', label: '全部' },
  ...ROLE_CONFIG.filter(r => r.key !== 'unknown').map(r => ({
    key: r.key,
    label: r.label,
  })),
]
