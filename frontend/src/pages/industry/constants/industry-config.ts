/**
 * Industry domain display constants — status labels/colors, score tiers.
 * Labels mirror backend app/domains/industry/constants/status_config.py.
 */

import type { CSSProperties } from 'react'

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

/** Match-score visual tiers: S 金紫 / A+ 蓝 / A 绿 / B+ 橙 / C 灰 */
export function scoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return '#94a3b8'
  if (score >= 100) return '#722ed1' // S — 金紫
  if (score >= 95) return '#1677ff'  // A+ — 蓝
  if (score >= 90) return '#389e0d'  // A — 绿
  if (score >= 80) return '#d4660a'  // B+ — 橙
  return '#94a3b8'                   // C — 灰
}

/** Soft background tint for each grade tier */
export function scoreBg(score: number | null | undefined): string {
  if (score === null || score === undefined) return '#f1f5f9'
  if (score >= 100) return '#f9f0ff'
  if (score >= 95) return '#e6f4ff'
  if (score >= 90) return '#f6ffed'
  if (score >= 80) return '#fff7e6'
  return '#f1f5f9'
}

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—'
  if (score >= 100) return 'S'
  if (score >= 95) return 'A+'
  if (score >= 90) return 'A'
  if (score >= 80) return 'B+'
  return 'C'
}

/**
 * Premium grade badge style generator.
 *
 * Design language (inspired by game rank badges / medal UI):
 * - S:     gold gradient + purple glow + white text (top prestige)
 * - A+:    blue gradient + blue glow + white text
 * - A:     green gradient + green glow + white text
 * - B+:    orange gradient + orange glow + white text
 * - C:     grey gradient + no glow + white text
 * - null:  flat grey + no glow + grey text
 *
 * Each badge uses a diagonal gradient (metallic sheen), an inset top
 * highlight (beveled 3D edge), and a tinted drop shadow (floating feel).
 *
 * @param size pixel size of the badge (width = height)
 * @returns CSSProperties for the badge container
 */
export function badgeStyle(
  score: number | null | undefined,
  size: number = 44
): CSSProperties {
  const fontSize = Math.round(size * 0.4)
  const radius = Math.round(size * 0.25)
  const glowSize = Math.round(size * 0.15)

  const base: CSSProperties = {
    width: size,
    height: size,
    borderRadius: radius,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    lineHeight: 1,
    flexShrink: 0,
    fontSize,
    fontWeight: 800,
    color: '#fff',
    textShadow: '0 1px 2px rgba(0,0,0,0.2)',
  }

  if (score === null || score === undefined) {
    return {
      ...base,
      background: 'linear-gradient(135deg, #e2e8f0, #cbd5e1)',
      color: '#64748b',
      textShadow: 'none',
    }
  }

  // Tier-specific gradients + glow shadows
  const tiers: { min: number; bg: string; glow: string }[] = [
    { min: 100, bg: 'linear-gradient(135deg, #9254de, #5b21b6)', glow: `0 0 ${glowSize}px rgba(114,46,209,0.5)` },
    { min: 95, bg: 'linear-gradient(135deg, #4096ff, #0958d9)', glow: `0 ${glowSize * 0.4}px ${glowSize}px rgba(22,119,255,0.35)` },
    { min: 90, bg: 'linear-gradient(135deg, #52c41a, #389e0d)', glow: `0 ${glowSize * 0.4}px ${glowSize}px rgba(82,196,26,0.35)` },
    { min: 80, bg: 'linear-gradient(135deg, #fa8c16, #d4660a)', glow: `0 ${glowSize * 0.4}px ${glowSize}px rgba(250,140,22,0.35)` },
  ]

  for (const tier of tiers) {
    if (score >= tier.min) {
      return {
        ...base,
        background: tier.bg,
        boxShadow: `inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -1px 0 rgba(0,0,0,0.1), ${tier.glow}`,
      }
    }
  }

  // C tier (below 80)
  return {
    ...base,
    background: 'linear-gradient(135deg, #b0b8c4, #8b95a3)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.2)',
  }
}
