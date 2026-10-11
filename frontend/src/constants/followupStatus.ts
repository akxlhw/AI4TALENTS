/**
 * Followup Status Constants
 *
 * Unified followup status definitions for talent pipeline management.
 * Used in favorites, talent pools, and talent detail views.
 *
 * i18n: `text` holds an i18n KEY (common namespace) — translate at render
 * time via useFollowupStatus() (components) or t(); the plain getters
 * translate through the i18n instance so legacy callers keep working.
 */

import { useTranslation } from 'react-i18next'
import { i18n } from '../i18n'

export interface FollowupStatusConfig {
  color: string
  text: string
}

/**
 * Followup status display configuration map.
 * NOTE: `text` holds an i18n KEY — translate with t() or useFollowupStatus().
 */
export const FOLLOWUP_STATUS_MAP: Record<string, FollowupStatusConfig> = {
  new_found: { color: 'blue', text: 'common:followupStatus.new_found' },
  reviewed: { color: 'cyan', text: 'common:followupStatus.reviewed' },
  followed: { color: 'green', text: 'common:followupStatus.followed' },
  pending_evaluation: { color: 'orange', text: 'common:followupStatus.pending_evaluation' },
  recommend_contact: { color: 'purple', text: 'common:followupStatus.recommend_contact' },
  no_followup: { color: 'default', text: 'common:followupStatus.no_followup' },
}

/**
 * Get followup status config with fallback
 *
 * @param status - Followup status string
 * @returns FollowupStatusConfig with color and translated display text
 */
export function getFollowupStatusConfig(status: string): FollowupStatusConfig {
  const base = FOLLOWUP_STATUS_MAP[status] || { color: 'default', text: '' }
  return { ...base, text: getFollowupStatusText(status) }
}

/**
 * Get followup status display text
 */
export function getFollowupStatusText(status: string): string {
  return i18n.t(`followupStatus.${status}`, { ns: 'common', defaultValue: status })
}

/**
 * Get followup status color
 */
export function getFollowupStatusColor(status: string): string {
  return (FOLLOWUP_STATUS_MAP[status] || { color: 'default', text: '' }).color
}

/** Render-side translated followup status labels (components only). */
export const useFollowupStatus = () => {
  const { t } = useTranslation('common')
  return {
    text: (status: string) => t(`followupStatus.${status}`, { defaultValue: status }),
    color: getFollowupStatusColor,
    config: (status: string): FollowupStatusConfig => ({
      color: getFollowupStatusColor(status),
      text: t(`followupStatus.${status}`, { defaultValue: status }),
    }),
  }
}
