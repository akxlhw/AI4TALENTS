/**
 * Shared role configuration for the AI Native lab domain.
 *
 * Single source of truth for role keys, colors, and academic level keys.
 * All lab components should import from here instead of defining their own.
 *
 * `labelKey` holds an i18n key in the `lab` namespace — translate at render
 * time via useLabRoles(); outside components fall back to the raw key.
 */
import { useTranslation } from 'react-i18next'
import '../../../i18n/namespaces/lab'

export interface RoleConfig {
  key: string
  labelKey: string
  /** Primary color for tags, dots, bars (hex — ECharts canvas can't use CSS vars) */
  color: string
}

/** Role display config — ordered by visual priority. */
export const ROLE_CONFIG: RoleConfig[] = [
  { key: 'professor', labelKey: 'role.professor', color: '#0D2B4E' },
  { key: 'student', labelKey: 'role.student', color: '#0EA5E9' },
  { key: 'graduate', labelKey: 'role.graduate', color: '#F59E0B' },
  { key: 'alumni', labelKey: 'role.alumni', color: '#0284C7' },
  { key: 'unknown', labelKey: 'role.unknown', color: '#CBD5E1' },
]

/** Quick lookup maps derived from ROLE_CONFIG */
export const ROLE_LABEL_KEYS: Record<string, string> = Object.fromEntries(
  ROLE_CONFIG.map(r => [r.key, r.labelKey])
)

export const ROLE_COLORS: Record<string, string> = Object.fromEntries(
  ROLE_CONFIG.map(r => [r.key, r.color])
)

/** Academic level keys (order drives filter option order) */
export const LEVEL_KEYS = ['phd', 'master', 'bachelor'] as const

/** Render-side translated role/level labels (components only). */
export const useLabRoles = () => {
  const { t } = useTranslation('lab')
  return {
    roleLabel: (key: string) =>
      t(ROLE_CONFIG.find(r => r.key === key)?.labelKey ?? '', { defaultValue: key }),
    levelLabel: (key: string) => t(`level.${key}`, { defaultValue: key }),
  }
}

/** Role filter options for search, translated (includes "全部角色") */
export const useRoleFilterOptions = () => {
  const { t } = useTranslation('lab')
  return [
    { label: t('search.allRoles'), value: '' },
    ...ROLE_CONFIG.filter(r => r.key !== 'unknown').map(r => ({
      label: t(r.labelKey),
      value: r.key,
    })),
  ]
}

/** Role tab config for lab detail page, translated (includes "全部") */
export const useRoleTabConfig = () => {
  const { t } = useTranslation('lab')
  return [
    { key: '', label: t('search.all') },
    ...ROLE_CONFIG.filter(r => r.key !== 'unknown').map(r => ({
      key: r.key,
      label: t(r.labelKey),
    })),
  ]
}
