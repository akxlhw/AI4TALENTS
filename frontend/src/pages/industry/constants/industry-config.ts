/**
 * Industry domain display constants — status labels/colors, score tiers.
 * Labels mirror backend app/domains/industry/constants/status_config.py.
 */

// Candidate recruiting status (position-talent link)
export const CANDIDATE_STATUS_LABELS: Record<string, string> = {
  new: '新候选人',
  contacted: '已触达',
  interviewed: '面试中',
  rejected: '已淘汰',
  hired: '已入职',
}

// Ant Design Tag preset colors: new 蓝 / contacted 橙 / interviewed 紫 / rejected 灰 / hired 绿
export const CANDIDATE_STATUS_COLORS: Record<string, string> = {
  new: 'blue',
  contacted: 'orange',
  interviewed: 'purple',
  rejected: 'default',
  hired: 'green',
}

export const CANDIDATE_STATUS_OPTIONS = Object.entries(CANDIDATE_STATUS_LABELS).map(
  ([value, label]) => ({ value, label })
)

// Position lifecycle
export const POSITION_STATUS_LABELS: Record<string, string> = {
  open: '在招',
  closed: '已关闭',
  archived: '已归档',
}

export const POSITION_STATUS_COLORS: Record<string, string> = {
  open: 'green',
  closed: 'orange',
  archived: 'default',
}

export const SOURCE_PLATFORM_LABELS: Record<string, string> = {
  maimai: '脉脉',
  linkedin: 'LinkedIn',
}

export const SOURCE_PLATFORM_OPTIONS = [
  { value: 'maimai', label: '脉脉' },
  { value: 'linkedin', label: 'LinkedIn' },
]

export const INDUSTRY_SORT_OPTIONS = [
  { value: 'match_score_desc', label: '匹配分降序' },
  { value: 'match_score_asc', label: '匹配分升序' },
  { value: 'created_desc', label: '最近导入' },
  { value: 'name_asc', label: '姓名升序' },
]

export const MIN_SCORE_OPTIONS = [
  { value: 0, label: '不限分数' },
  { value: 60, label: '60 分以上' },
  { value: 70, label: '70 分以上' },
  { value: 80, label: '80 分以上' },
  { value: 90, label: '90 分以上' },
]

/** Match-score visual tiers: S 紫 / A+ 蓝 / A 绿 / B+ 橙 / 其余灰 */
export function scoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return '#94a3b8'
  if (score >= 100) return '#722ed1' // S — 紫色
  if (score >= 95) return '#1677ff'  // A+ — 蓝色
  if (score >= 90) return '#52c41a'  // A — 绿色
  if (score >= 80) return '#fa8c16'  // B+ — 橙色
  return '#94a3b8'                   // C — 灰色
}

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—'
  if (score >= 100) return 'S'
  if (score >= 95) return 'A+'
  if (score >= 90) return 'A'
  if (score >= 80) return 'B+'
  return 'C'
}
