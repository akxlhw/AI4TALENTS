/**
 * Role Type Constants
 *
 * Unified role type definitions for academic talent identification.
 * This file provides a single source of truth for role type display
 * configuration across the frontend application.
 *
 * Role Types:
 * - professor: 教授/研究员 (h_index >= 25 or high citation count)
 * - student: 在读学生 (works <= 8 and low citations)
 * - graduate: 毕业/早期研究者 (8 < works < 30, transitioning)
 * - unknown: 未知 (insufficient data)
 *
 * i18n: `text` holds an i18n KEY (common namespace) — translate at render
 * time via useRoleType() (components) or t(); the plain getters translate
 * through the i18n instance so legacy callers keep working.
 */

import { useTranslation } from 'react-i18next'
import { i18n } from '../i18n'

export type RoleTypeValue = 'professor' | 'student' | 'graduate' | 'unknown'

export interface RoleTypeConfig {
  color: string
  text: string
}

/**
 * Role type display configuration map.
 * NOTE: `text` holds an i18n KEY — translate with t() or useRoleType().
 */
export const ROLE_TYPE_MAP: Record<RoleTypeValue, RoleTypeConfig> = {
  professor: { color: 'green', text: 'common:roleType.professor' },
  student: { color: 'blue', text: 'common:roleType.student' },
  graduate: { color: 'orange', text: 'common:roleType.graduate' },
  unknown: { color: 'default', text: 'common:roleType.unknown' },
}

/**
 * Legacy role type mappings for backward compatibility
 * Maps old role types to new unified types
 */
export const LEGACY_ROLE_TYPE_MAP: Record<string, RoleTypeValue> = {
  // Old values that need to be mapped
  graduated: 'graduate',
  teaching_research: 'professor',
  associate_professor: 'professor',
  researcher: 'graduate',
  phd_student: 'student',
  master_student: 'student',
}

const normalizeRoleType = (roleType: string): RoleTypeValue | 'unknown' => {
  const normalizedType = LEGACY_ROLE_TYPE_MAP[roleType] || roleType
  return (normalizedType in ROLE_TYPE_MAP ? normalizedType : 'unknown') as RoleTypeValue
}

/**
 * Get role type configuration with backward compatibility
 *
 * @param roleType - Role type string (may be legacy or current)
 * @returns RoleTypeConfig with color and translated display text
 */
export function getRoleTypeConfig(roleType: string): RoleTypeConfig {
  const value = normalizeRoleType(roleType)
  return {
    color: ROLE_TYPE_MAP[value].color,
    text: getRoleTypeText(value),
  }
}

/**
 * Get display text for a role type
 *
 * @param roleType - Role type string (may be legacy or current)
 * @returns Translated display text (falls back to the raw value when unknown)
 */
export function getRoleTypeText(roleType: string): string {
  const value = normalizeRoleType(roleType)
  return i18n.t(`roleType.${value}`, { ns: 'common', defaultValue: value })
}

/**
 * Get color for a role type
 *
 * @param roleType - Role type string
 * @returns Ant Design tag color
 */
export function getRoleTypeColor(roleType: string): string {
  return ROLE_TYPE_MAP[normalizeRoleType(roleType)].color
}

/**
 * Check if a role type is valid
 *
 * @param roleType - Role type string to validate
 * @returns true if valid role type
 */
export function isValidRoleType(roleType: string): roleType is RoleTypeValue {
  return roleType in ROLE_TYPE_MAP
}

/**
 * Get all role type options for select/ filter components
 *
 * @returns Array of role type options with value and translated label
 */
export function getRoleTypeOptions(): Array<{ value: RoleTypeValue; label: string }> {
  return (Object.keys(ROLE_TYPE_MAP) as RoleTypeValue[]).map(value => ({
    value,
    label: getRoleTypeText(value),
  }))
}

/** Render-side translated role type labels (components only). */
export const useRoleType = () => {
  const { t } = useTranslation('common')
  return {
    text: (roleType: string) =>
      t(`roleType.${LEGACY_ROLE_TYPE_MAP[roleType] || roleType}`, { defaultValue: roleType }),
    color: getRoleTypeColor,
    options: (): Array<{ value: RoleTypeValue; label: string }> =>
      (Object.keys(ROLE_TYPE_MAP) as RoleTypeValue[]).map(value => ({
        value,
        label: t(`roleType.${value}`, { defaultValue: value }),
      })),
  }
}
