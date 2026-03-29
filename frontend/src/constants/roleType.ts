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
 */

export type RoleTypeValue = 'professor' | 'student' | 'graduate' | 'unknown'

export interface RoleTypeConfig {
  color: string
  text: string
}

/**
 * Role type display configuration map
 */
export const ROLE_TYPE_MAP: Record<RoleTypeValue, RoleTypeConfig> = {
  professor: { color: 'green', text: '教授/研究员' },
  student: { color: 'blue', text: '学生' },
  graduate: { color: 'orange', text: '毕业生' },
  unknown: { color: 'default', text: '未知' },
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

/**
 * Get role type configuration with backward compatibility
 *
 * @param roleType - Role type string (may be legacy or current)
 * @returns RoleTypeConfig with color and display text
 */
export function getRoleTypeConfig(roleType: string): RoleTypeConfig {
  // First, check if it's a legacy type that needs mapping
  const normalizedType = LEGACY_ROLE_TYPE_MAP[roleType] || roleType

  // Return config for the normalized type, fallback to unknown
  return ROLE_TYPE_MAP[normalizedType as RoleTypeValue] || ROLE_TYPE_MAP.unknown
}

/**
 * Get display text for a role type
 *
 * @param roleType - Role type string
 * @returns Chinese display text
 */
export function getRoleTypeText(roleType: string): string {
  return getRoleTypeConfig(roleType).text
}

/**
 * Get color for a role type
 *
 * @param roleType - Role type string
 * @returns Ant Design tag color
 */
export function getRoleTypeColor(roleType: string): string {
  return getRoleTypeConfig(roleType).color
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
 * @returns Array of role type options with value and label
 */
export function getRoleTypeOptions(): Array<{ value: RoleTypeValue; label: string }> {
  return [
    { value: 'professor', label: '教授/研究员' },
    { value: 'student', label: '学生' },
    { value: 'graduate', label: '毕业生' },
    { value: 'unknown', label: '未知' },
  ]
}
